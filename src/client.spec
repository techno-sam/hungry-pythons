# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

data_files = [("../assets/*","assets")]

a = Analysis(['client.py'],
             pathex=['/home/sam/bin/0_packaged_programs/hungry_pythons/src'],
             binaries=[],
             datas=data_files,
             hiddenimports=['pkg_resources.py2_warn','network','netstring'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='client',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
'''coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='client')'''
