#!/bin/bash
set -e

# 检查是否有持久化的状态
if [ -d "/var/lib/openstack/state/keystone" ]; then
    echo "恢复Keystone配置..."
    cp -r /var/lib/openstack/state/keystone/* /etc/keystone/
    chown -R keystone:keystone /etc/keystone
fi

if [ -d "/var/lib/openstack/state/nova" ]; then
    echo "恢复Nova配置..."
    cp -r /var/lib/openstack/state/nova/* /etc/nova/
    chown -R nova:nova /etc/nova
fi

if [ -d "/var/lib/openstack/state/glance" ]; then
    echo "恢复Glance配置..."
    cp -r /var/lib/openstack/state/glance/* /etc/glance/
    chown -R glance:glance /etc/glance
fi

if [ -d "/var/lib/openstack/state/neutron" ]; then
    echo "恢复Neutron配置..."
    cp -r /var/lib/openstack/state/neutron/* /etc/neutron/
    chown -R neutron:neutron /etc/neutron
fi

if [ -d "/var/lib/openstack/state/cinder" ]; then
    echo "恢复Cinder配置..."
    cp -r /var/lib/openstack/state/cinder/* /etc/cinder/
    chown -R cinder:cinder /etc/cinder
fi

echo "服务状态恢复完成"
exit 0
