#!/bin/bash

#sudo vim  /run/systemd/resolve/resolv.conf
#sudo vim /etc/hosts
#sudo vim /etc/hosts
#source /etc/environment

oldIP=$1
newIP=$2
echo "$oldIP/$newIP"

echo "*****************************************************"
echo "              Rewrite the manifest file"
echo "*****************************************************"
cd /etc/kubernetes/manifests/
sudo sed -i s/$oldIP/$newIP/g kube-apiserver.yaml
sudo sed -i s/$oldIP/$newIP/g kube-controller-manager.yaml
sudo sed -i s/$oldIP/$newIP/g kube-scheduler.yaml
sudo sed -i s/$oldIP/$newIP/g etcd.yaml
wait
echo "Done\n\n"

echo "*****************************************************"
echo "              Regenerate the certs"
echo "*****************************************************"

cd /etc/kubernetes/pki
sudo rm apiserver.crt apiserver.key
sudo kubeadm init phase certs apiserver
wait
sudo rm etcd/peer.crt etcd/peer.key
sudo kubeadm init phase certs etcd-peer
wait
sudo kubeadm init phase certs all
wait
echo "Done\n\n"

echo "*****************************************************"
echo "              Regenerate the conf file"
echo "*****************************************************"

cd /etc/kubernetes
sudo rm -f admin.conf kubelet.conf controller-manager.conf scheduler.conf
sudo kubeadm init phase kubeconfig all
wait
sudo cp /etc/kubernetes/admin.conf /home/smartedge-open/.kube/config
wait
sudo chown $USER:$USER $HOME/.kube/config
wait
echo "Done\n\n"

echo "*****************************************************"
echo "              Restart the services"
echo "*****************************************************"

systemctl restart container
wait
systemctl restart kubelet.service

wait 
echo "Done\n\n"

kubectl get pods -A


