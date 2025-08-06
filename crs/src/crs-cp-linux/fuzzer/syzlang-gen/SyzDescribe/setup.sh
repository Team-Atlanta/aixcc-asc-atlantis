#!/bin/bash

#should be python 3.10+
apt update

apt install -y python3 python3-venv cmake git

apt install -y llvm clang lld bc

# kernel build dependencies
apt install -y libelf-dev


# Function to check if an environment variable is set
check_env_var() {
    local var_name=$1
    if [ -z "${!var_name}" ]; then
        echo "Error: Environment variable $var_name is not set."
        exit 1
    fi
}

# Check each required environment variable
#check_env_var "LITELLM_KEY"
#check_env_var "AIXCC_LITELLM_HOSTNAME"

bash script/build.bash

# Check if the directory ./syzdescribe_env exists
if [ ! -d "./syzdescribe_env" ]; then
    # If the directory does not exist, create a virtual environment
    python3 -m venv syzdescribe_venv
    echo "Virtual environment syzdescribe_venv created."
fi

source syzdescribe_venv/bin/activate

