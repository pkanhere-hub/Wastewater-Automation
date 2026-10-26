import sys
t=open('template.html').read()
svg=open('schematic.svg').read().replace('viewBox="0 0 1280 720"','viewBox="0 40 1280 630"')
page=t.replace('<!--SCHEMATIC-->',svg)
open('mbbr-plant.html','w').write(page.replace('<!--PWA_HEAD-->','').replace('<!--PWA_SCRIPT-->',''))
head='''<meta name="theme-color" content="#17222c">
<meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">'''
script='''<script>
if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
</script>'''
doc='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}[hidden]{display:none!important}</style>\n'
p=page.replace('<!--PWA_HEAD-->',head).replace('<!--PWA_SCRIPT-->',script)
i=p.index('<div class="app">')
open('pwa/index.html','w').write(doc+p[:i]+'</head>\n<body>\n'+p[i:]+'\n</body>\n</html>\n')
