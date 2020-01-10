import traceback

def onData(instance, args):
  data = args[0].data

  try:
    if data is None or not isinstance(data, dict) or 'path' not in data:
      # No correct input
      if not 'filename' in instance.options:
        return

      path = instance.options['filename']
      enc = instance.options['encoding'] if 'encoding' in instance.options else 'UTF-8'
      type = instance.options['type'] if 'type' in instance.options else 'buffer'
    else:
      path = data['path']
      enc = instance.options['encoding'] if 'encoding' in data else 'UTF-8'
      type = instance.options['type'] if 'type' in data else 'buffer'

    if type == 'buffer':
      file = open(path, 'rb')
    else:
      file = open(path, 'r', encoding=enc)

    toSend = file.read()
    file.close()
    instance.send(toSend)
  except Exception as e:
    instance.throw(str(e) + '\n' + str(traceback.extract_stack()))

def install(instance):
  instance.on('data', onData)

EXPORTS = {
  'id': 'filereader',
  'title': 'File Reader',
  'author': 'Arthur Chevalier',
  'color': '#989D78',
  'output': 1,
  'input': 1,
  'icon': 'file-text-o',
  'version': '1.0.1',
  'group': 'Inputs',
  'options': {
    'filename': '',
    'append': True,
    'delimiter': '\\n'
  },
  'readme': """# File Reader

This component reads a file from file system.

## Input
If incomming object has a path property then filename option is ignored.

Example of incomming object
\`\`\`javascript
{
	path: '/public/robots.txt',
	type: 'text', // optional, default text
	encoding: 'utf8' // optional, default utf8
}
\`\`\`
""",
  'html': """<div class="padding">
	<div class="row">
		<div class="col-md-6">
			<div data-jc="textbox" data-jc-path="filename" data-jc-config="placeholder:/public/robots.txt">Filename</div>
			<div class="help m">Filename relative to the application root.</div>
		</div>
	</div>
	<div class="row">
		<div class="col-md-6">
			<div data-jc="dropdown" data-jc-path="type" data-jc-config="items:Buffer|buffer,Text|text">Read as</div>
		</div>
		<div class="col-md-6">
			<div data-jc="textbox" data-jc-path="encoding" data-jc-config="placeholder:utf8">Encoding (default 'utf8')</div>
			<div class="help m">Only for 'Read as text'</div>
		</div>
	</div>
</div>""",
  'install': install
}