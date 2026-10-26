param(
    [Parameter(Mandatory = $true)]
    [string]$DomainName,

    [Parameter(Mandatory = $true)]
    [string]$KeyName,

    [string]$Profile = "dosje-dev",
    [string]$Region = "ap-southeast-2",
    [string]$InstanceType = "t3.large",
    [string]$Repository = "https://github.com/rksrohiit/AICTE-application.git",
    [string]$Branch = "rksrohiit-analyze-repository"
)

$ErrorActionPreference = "Stop"

function Invoke-AwsJson {
    param([string[]]$Arguments)
    $result = & aws @Arguments --profile $Profile --region $Region
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed: aws $($Arguments -join ' ')"
    }
    return ($result | ConvertFrom-Json)
}

$identity = Invoke-AwsJson @("sts", "get-caller-identity")
Write-Host "Deploying as $($identity.Arn) in $Region"

$vpc = Invoke-AwsJson @(
    "ec2", "describe-vpcs",
    "--filters", "Name=is-default,Values=true",
    "--query", "Vpcs[0]",
    "--output", "json"
)
if ($null -eq $vpc.VpcId) {
    throw "No default VPC exists in $Region. Create a VPC and subnet before deployment."
}

$subnet = Invoke-AwsJson @(
    "ec2", "describe-subnets",
    "--filters", "Name=vpc-id,Values=$($vpc.VpcId)",
    "--query", "Subnets[0]",
    "--output", "json"
)
if ($null -eq $subnet.SubnetId) {
    throw "No public subnet with MapPublicIpOnLaunch enabled exists in the default VPC."
}

$sgName = "aicte-web-$($DomainName.Replace('.', '-'))"
$existingSg = Invoke-AwsJson @(
    "ec2", "describe-security-groups",
    "--filters", "Name=vpc-id,Values=$($vpc.VpcId)", "Name=group-name,Values=$sgName",
    "--query", "SecurityGroups[0]",
    "--output", "json"
)

if ($null -eq $existingSg.GroupId) {
    $securityGroup = Invoke-AwsJson @(
        "ec2", "create-security-group",
        "--group-name", $sgName,
        "--description", "AICTE HTTPS web gateway",
        "--vpc-id", $vpc.VpcId,
        "--tag-specifications", "ResourceType=security-group,Tags=[{Key=Name,Value=$sgName},{Key=ManagedBy,Value=deploy-ec2.ps1}]",
        "--output", "json"
    )
    $groupId = $securityGroup.GroupId
} else {
    $groupId = $existingSg.GroupId
}

$rules = @(
    @{ Port = 80; Description = "HTTP for ACME and redirect" },
    @{ Port = 443; Description = "HTTPS application traffic" }
)
foreach ($rule in $rules) {
    try {
        & aws ec2 authorize-security-group-ingress `
            --group-id $groupId `
            --protocol tcp `
            --port $rule.Port `
            --cidr 0.0.0.0/0 `
            --description $rule.Description `
            --profile $Profile `
            --region $Region 2>$null
    } catch {
        Write-Host "Ingress rule for port $($rule.Port) already exists or could not be added; continuing."
    }
}

$userData = @"
#!/bin/bash
set -euxo pipefail
dnf update -y
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user
mkdir -p /opt/aicte
git clone --branch '$Branch' '$Repository' /opt/aicte/app
cd /opt/aicte/app
cp backend/.env.example backend/.env
sed -i 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$DomainName|' backend/.env
sed -i 's|^DEBUG=.*|DEBUG=false|' backend/.env
mkdir -p deploy/certbot/conf deploy/certbot/www
cat > /opt/aicte/README-FIRST.txt <<'EOF'
Before starting the production overlay:
1. Set production secrets in /opt/aicte/app/backend/.env.
2. Point DNS for $DomainName to this instance.
3. Obtain the certificate files under deploy/certbot/conf/live/$DomainName/.
4. Run: DOMAIN_NAME=$DomainName docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
EOF
"@

$encodedUserData = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userData))
$ami = & aws ssm get-parameter `
    --name "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64" `
    --query "Parameter.Value" `
    --output text `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ami)) {
    throw "Unable to resolve the latest Amazon Linux 2023 AMI."
}

$run = Invoke-AwsJson @(
    "ec2", "run-instances",
    "--image-id", $ami,
    "--instance-type", $InstanceType,
    "--key-name", $KeyName,
    "--subnet-id", $subnet.SubnetId,
    "--security-group-ids", $groupId,
    "--associate-public-ip-address",
    "--metadata-options", "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=2",
    "--block-device-mappings", "DeviceName=/dev/xvda,Ebs={VolumeSize=50,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}",
    "--user-data", $encodedUserData,
    "--tag-specifications", "ResourceType=instance,Tags=[{Key=Name,Value=AICTE-Validation-Platform},{Key=ManagedBy,Value=deploy-ec2.ps1}]",
    "--query", "Instances[0]",
    "--output", "json"
)

Write-Host "Instance launched: $($run.InstanceId)"
Write-Host "Wait for the public address with:"
Write-Host "aws ec2 describe-instances --instance-ids $($run.InstanceId) --query 'Reservations[0].Instances[0].[PublicIpAddress,PublicDnsName,State.Name]' --output table --profile $Profile --region $Region"
