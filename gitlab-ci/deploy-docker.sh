#!/bin/bash
cd ~/ci/beos-core/$CI_COMMIT_REF_NAME

if [ -z "$BEOS_REVISION" ]
then
  export BEOS_REVISION=`date +'beos-testnet.%Y%m%d'`
fi

if [ -z "$BEOS_VERSION_TAG" ]
then
  export BEOS_VERSION_TAG=$(git describe --tag)
fi

echo "Variable 'BEOS_TESTNET_DOCKER_REPOSITORY' ->" $BEOS_TESTNET_DOCKER_REPOSITORY
echo "Variable 'BEOS_REVISION' ->" $BEOS_REVISION
echo "Variable 'BEOS_VERSION_TAG' ->" $BEOS_VERSION_TAG
echo "Variable 'P2P_PEER_ADDRESS' ->" $P2P_PEER_ADDRESS
echo "Variable 'BEOS_DOCKER_LATEST' ->" $BEOS_DOCKER_LATEST

cd cd-scripts

cp config-$CI_BEOS_CONFIG_NAME.py config.py

if ! ./deploy.py --build-beos
then
  cat beos_deploy_main.log
  printf "Unable to build beos project. Exiting..."
  exit 1
fi

cat beos_deploy_main.log

cd ..

if [ ! -d "docker-deploy" ];
then
  git clone git@gitlab.syncad.com:blocktrades/docker.git docker-deploy
fi

cd docker-deploy
cd beos-testnet

cp ~/ci/beos-core/$CI_COMMIT_REF_NAME/build/programs/nodeos/nodeos ./node/
cp ~/ci/beos-core/$CI_COMMIT_REF_NAME/build/resources/genesis.json ./node/
cp ~/ci/beos-core/$CI_COMMIT_REF_NAME/build/programs/keosd/keosd ./wallet/

cd node

if ! sed -i "s/#p2p-peer-address/p2p-peer-address = $P2P_PEER_ADDRESS/" config.ini
then
  printf "Cannot replace p2p-peer-address."
  exit 1
fi

cd ..

ls -al node
ls -al wallet

cd node

if ! make
then
  printf "Cannot deploy nodeos images to registry"
fi

cd ../wallet

if ! make
then
  printf "Cannot deploy keosd images to registry"
fi

echo "Clean up images which built in this job"

docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/keosd:$BEOS_VERSION_TAG -f
docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/keosd:$BEOS_REVISION -f
docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/keosd:latest -f
docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/nodeos:$BEOS_VERSION_TAG -f
docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/nodeos:$BEOS_REVISION -f
docker rmi registry.gitlab.syncad.com/blocktrades/docker/beos-testnet/nodeos:latest -f