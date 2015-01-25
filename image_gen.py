#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from subprocess import Popen, PIPE
from inspect import cleandoc
from jinja2 import Template
from yaml import load
try:
  from yaml import CLoader as Loader
except ImportError:
  from yaml import Loader

from clint.arguments import Args 
from clint.textui import puts, colored, indent

import codecs

args = Args()

deployment_file = os.path.abspath('deployment.yaml')

template_dir = 'files'
res_dir = 'files_gen'
imagebuilder_dir = 'OpenWrt-ImageBuilder-ar71xx_generic-for-linux-x86_64'

abs_template = os.path.abspath(template_dir)
abs_res = os.path.join(os.path.split(abs_template)[0], res_dir)
abs_imagebuilder = os.path.abspath(imagebuilder_dir)

def render_file(original):
  template = cleandoc(original) + '\n\n'

  return Template(template)

def write_rendered_file(abs_template_path, full_file_path, prefix, content):
  file_mask = os.stat(full_file_path).st_mode & 0777
  file_dir_path = os.path.split(full_file_path)[0]
  file_dir_mask = os.stat(file_dir_path).st_mode & 0777
  path = os.path.relpath(full_file_path, abs_template_path)

  res_full_file_path = os.path.join(os.path.join(abs_res, prefix), path)
  res_file_dir_path = os.path.split(res_full_file_path)[0]

  # create missing dirs or adjust mode
  # TODO: handle broken symlinks for init.d
  if os.path.exists(res_file_dir_path):
    res_file_dir_mask = os.stat(res_file_dir_path).st_mode & 0777
    if res_file_dir_mask != file_dir_mask:
      os.chmod(res_file_dir_path, file_dir_mask)
  else:
    # TODO: handle subdirs
    os.makedirs(res_file_dir_path, file_dir_mask)

  with open(res_full_file_path, 'w') as f:
    f.write(content)

  os.chmod(res_full_file_path, file_mask)


def generate_images(c, profile):
  pkgs = ' '.join(c['global']['pkgs'])
  files = os.path.join(abs_res, c['router']['hostname'])
  bin_dir = '{}/images_gen/{}'.format(os.path.split(abs_template)[0], c['router']['hostname'])

  if os.path.exists(bin_dir):
    shutil.rmtree(bin_dir)

  os.makedirs(bin_dir, 493)

  make_cmd = [
              '/usr/bin/make', 
              '-C',
              abs_imagebuilder,
              'image',
              'PROFILE={}'.format(profile), 
              'FILES={}'.format(files),
              'BIN_DIR={}'.format(bin_dir),
              'PACKAGES={}'.format(pkgs)
            ]

  puts(colored.blue('runing cmd:'))
  puts(colored.green(' '.join(make_cmd)))

  p = Popen(make_cmd, stdout=PIPE, stderr=PIPE, bufsize=1)
  for line in iter(p.stdout.readline, b''):
    print line,
  p.communicate()

def rexec(rconfig, cmd):
  exec_cmd = [
          'ssh',
          '-o',
          'ServerAliveInterval=5',
          'root@{}'.format(rconfig['network']['mgmt']['ip']),
          cmd
          ]

  p = Popen(exec_cmd, stdout=PIPE, stderr=PIPE, bufsize=1)
  for line in iter(p.stdout.readline, b''):
    print line,
  p.communicate()

def upload_file(rconfig, abs_file_path, upload_dir):
  upload_cmd = [
                'scp',
                 abs_file_path,
                 'root@{}:{}'.format(rconfig['network']['mgmt']['ip'], upload_dir)
                 ]
  print(upload_cmd)

  p = Popen(upload_cmd, stdout=PIPE, stderr=PIPE, bufsize=1)
  for line in iter(p.stdout.readline, b''):
    print line,
    p.communicate()

if __name__ == '__main__':

  if ('-d' in args.grouped) and args.grouped['-d']:
    deployment_file = os.path.abspath(args.grouped['-d'].last)

  with open(deployment_file, 'r') as yamstream:
    config = load(yamstream, Loader=Loader)

  if ('--hostnames' in args.grouped) and args.grouped['--hostnames']:
    hostnames = args.grouped['--hostnames'].all
    valid_routers = [r for r in config['routers'] for h in hostnames if h == r['hostname']]

    if len(valid_routers) == len(hostnames):
      config['routers'] = valid_routers
    else:
      puts(colored.red('Requested hostname(s) doesn\'t exist in deployment yaml:'))
      for ir in [h for h in hostnames for vr in valid_routers if h != vr['hostname']]:
        puts(colored.red(ir))
      sys.exit(1)

  if '--munin-conf' in  args.grouped:
    group_name = 'wifi'
    dbs = '\\'

    if ('--munin-group' in  args.grouped) and args.grouped['--munin-group']:
      group_name = args.grouped['--munin-group'].last

    puts(colored.green('Generating sample munin config!\n'))
    puts('[{};global]'.format(group_name))
    with indent(4):
      puts('update no')
      puts('contacts no\n')
      puts('wificlients.update no')
      puts('wificlients.graph_category wifi')
      puts('wificlients.graph_title Total number of wifi clients')
      puts('wificlients.graph_total Number of clients')
      puts('wificlients.graph_scale no')
      puts('wificlients.graph_args --base 1000 -l 0')
      puts('wificlients.graph_order iad irl las')
      puts('wificlients.total.graph no')
      with indent(4):
        puts('wificlients.eduroam24.label Number of 2.4GHz eduroam clients')
        puts('wificlients.eduroam24.sum \\')
        with indent(4):
          for n, r in enumerate(config['routers']):
            if n == (len(config['routers']) - 1):
              dbs = ''
            puts('{};{}:wificlients_wlan0.clients {}'.format(group_name, r['hostname'], dbs))

    for r in config['routers']:
      puts('\n[{};{}]'.format(group_name, r['hostname']))
      with indent(4):
        puts('address {}'.format(r['network']['mgmt']['ip']))
        puts('use_node_name yes')
    sys.exit(0)

  if ('--upload-file' in  args.grouped) and args.grouped['--upload-file']:
    puts(colored.yellow('Going to file upload...'))
    upload_file = args.grouped['--upload-file'].last
    files_gen_abs = os.path.abspath(res_dir)
    for rconfig in config['routers']:
      abs_ufile = os.path.join(files_gen_abs, rconfig['hostname']) + upload_file
      upload_file(rconfig, os.path.join(abs_ufile, upload_file))

    puts(colored.yellow('Done uploading...'))
    sys.exit(0)

  if ('--exec' in  args.grouped) and args.grouped['--exec']:
    puts(colored.yellow('Exec command on remote router(s)..'))
    cmd = args.grouped['--exec'].last
    for rconfig in config['routers']:
      rexec(rconfig, cmd)

    puts(colored.yellow('Done execing...'))
    sys.exit(0)

  puts(colored.yellow('Going to config generation...'))
  for rconfig in config['routers']:
    c = {}
    res_router_dir = os.path.join(abs_res, rconfig['hostname'])
    router_profile = config['global']['default_profile'] if not rconfig.get('profile') else rconfig['profile']
    c['global'] = config['global']
    c['router'] = rconfig

    puts(colored.red('Generating config for: ') + colored.blue(rconfig['hostname']))
    # clean old config
    if os.path.exists(res_router_dir):
      shutil.rmtree(res_router_dir)

    # render generic config
    generic_dir = os.path.join(abs_template, 'generic')
    for root, subdirs, files in os.walk(generic_dir):
      for filename in files:
        file_path = os.path.join(root, filename)

        with open(file_path, 'rb') as f:
          f_content = f.read()

        r_file = render_file(f_content).render(**c)
        write_rendered_file(generic_dir, file_path, rconfig['hostname'], r_file)

    # render profile config
    profile_dir = os.path.join(os.path.join(abs_template, 'profiles'), router_profile)
    if os.path.exists(generic_dir):
      for root, subdirs, files in os.walk(profile_dir):
        for filename in files:
          file_path = os.path.join(root, filename)
          print file_path

          with open(file_path, 'rb') as f:
            f_content = f.read()

          r_file = render_file(f_content).render(**c)
          write_rendered_file(profile_dir, file_path, rconfig['hostname'], r_file)

    # hostname override config
    hostname_dir = os.path.join(os.path.join(abs_template, 'hostnames'), rconfig['hostname'])
    if os.path.exists(hostname_dir):
      for root, subdirs, files in os.walk(hostname_dir):
        for filename in files:
          file_path = os.path.join(root, filename)

          with open(file_path, 'rb') as f:
            f_content = f.read()

          r_file = render_file(f_content).render(**c)
          write_rendered_file(hostname_dir, file_path, rconfig['hostname'], r_file)

    puts(colored.green('Done generating conf!'))
    puts(colored.magenta('Generating image for: ') + colored.blue(rconfig['hostname']))
    generate_images(c, router_profile)
    puts(colored.magenta('Done generating image!'))
