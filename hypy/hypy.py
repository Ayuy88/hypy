#!/usr/bin/env python3
# coding: utf-8

import click
from modules import hvclient
from modules import printer
from modules import cache
from modules import config


@click.group()
@click.option('--user', '-u', help='Username in hyper-v server')
@click.option('passw', '--pass', '-p', help='Password in hyper-v server')
@click.option('--domain', '-d', help='Domain name')
@click.option('--host', '-m', help='Hyper-V server hostname/ip address')
@click.option('--proto', '-t', help='Protocol to be used',
              type=click.Choice(['ssh', 'winrm']))
def main(user, passw, domain, host, proto):
    """
    Multiplataform Hyper-V Manager using Python and FreeRDP
    """
    config.load(user, passw, domain, host, proto)
    hvclient.config = config.configuration
    cache.vms_cache_filename = config.configuration['cache_file']
    cache.sync_interval = config.configuration['sync_interval']


@main.command("list", help='List virtual machines and its indexes')
@click.option('--sync', '-s', is_flag=True, default=False,
              help='Syncronize with server updating local cache')
@click.option('--name', '-n', help='Filter virtual machines by name')
def list_vms(sync, name):
    if sync or cache.need_update():
        rs = hvclient.get_vm(name)
        vms = hvclient.parse_result(rs)
        cache.update_cache(vms)
    cache_vms = cache.list_vms()
    printer.print_list_vms(cache_vms, name)


@main.command("ls", help='List updated virtual machines and its indexes')
@click.option('--name', '-n', help='Filter virtual machines by name')
@click.pass_context
def ls(ctx, name):
    ctx.invoke(list_vms, sync=True, name=name)


@main.command(help='List virtual machine snapshots')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def snaps(ctx, name, index):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    rs = hvclient.get_vm(name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)
    rs_snaps = hvclient.list_vm_snaps(vm[0]['Name'])
    snaps = hvclient.parse_result(rs_snaps)
    printer.print_vm_snaps(snaps, vm[0]['Name'])


@main.command(help='Restore virtual machine snapshot')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.argument('snap_name')
@click.pass_context
def restore(ctx, name, index, snap_name):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    rs = hvclient.restore_vm_snap(name, snap_name)
    hvclient.parse_result(rs)


@main.command(help="Delete a machine's snapshot by name")
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.option('-r', is_flag=True, help="Remove snapshot's children as well")
@click.argument('snap_name')
@click.pass_context
def delete(ctx, name, index, snap_name, r):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    rs = hvclient.remove_vm_snapshot(name, snap_name, r)
    hvclient.parse_result(rs)


@main.command(help="Create a new snapshot with vm's current state")
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.argument('snap_name')
@click.pass_context
def create(ctx, name, index, snap_name):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    rs = hvclient.create_vm_snapshot(name, snap_name)
    hvclient.parse_result(rs)


@main.command(help="Connect to virtual machine identified by index")
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def connect(ctx, name, index):
    validate_input(ctx, name, index)

    if not name:
        vm_cache = cache.get_vm_by_index(index)
    else:
        vm_cache = cache.get_vm_by_name(name)

    vm_name = vm_cache['Name']
    vm_index = vm_cache['index']
    vm_id = vm_cache['Id']

    rs = hvclient.get_vm(vm_name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)

    if vm['State'] not in [2, 9]:
        rs = hvclient.start_vm(name)
        vm = hvclient.parse_result(rs)

    hvclient.connect(vm_name, vm_id, vm_index)


@main.command(help='Start virtual machine identified by index')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def start(ctx, name, index):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    hvclient.start_vm(name)
    rs = hvclient.get_vm(name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)


@main.command(help='Pause virtual machine identified by index')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def pause(ctx, name, index):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    hvclient.pause_vm(name)
    rs = hvclient.get_vm(name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)


@main.command(help='Resume (paused) virtual machine identified by index')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def resume(ctx, name, index):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    hvclient.resume_vm(name)
    rs = hvclient.get_vm(name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)


@main.command(help='Stop virtual machine identified by index')
@click.option('--force', '-f', is_flag=True, help='Hyper-V gives the guest\
 five minutes to save data, then forces a shutdown')
@click.option('--name', '-n', help='Use vm name instead of index')
@click.argument('index', required=False)
@click.pass_context
def stop(ctx, name, index, force):
    validate_input(ctx, name, index)

    if not name:
        name = cache.get_vm_by_index(index)['Name']

    hvclient.stop_vm(name, force)
    rs = hvclient.get_vm(name)
    vm = hvclient.parse_result(rs)
    cache.update_cache(vm)


def validate_input(ctx, name, index):
    """Additional input parameter validation"""
    if not (name or index) or (name and index):
        click.echo(ctx.get_help())
        exit(1)


if __name__ == "__main__":
    main()
