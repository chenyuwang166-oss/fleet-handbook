"""Small, offline SVG cards and browser-only PNG export (standard library)."""
from html import escape
import re
import unicodedata


def _xml(value):
    # XMLSerializer feeds an SVG image, so invalid XML control characters must
    # not survive even though HTML itself would accept them as text.
    value = ''.join(c if c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF or
                    0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
                    else '\ufffd' for c in str(value))
    return escape(value, quote=True)


def svg_text(value, x, y, size=24, fill='#3b2673', weight=400, anchor='start'):
    """An escaped SVG text node. Positions and visual attributes are constants."""
    return ('<text x="{}" y="{}" font-size="{}" fill="{}" font-weight="{}" '
            'text-anchor="{}">{}</text>').format(
                x, y, size, _xml(fill), weight, _xml(anchor), _xml(value))


def _width(value):
    return sum(0 if unicodedata.combining(c) else
               1 if unicodedata.east_asian_width(c) in ('W', 'F') else .66
               for c in value)


def text_lines(value, width, size=24):
    """Conservative native-font wrapping, including long unbroken identifiers."""
    limit = max(1, width / size)
    lines = []
    for paragraph in str(value).split('\n'):
        current = ''
        for token in re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*|\s+|.", paragraph):
            if current and _width(current + token) > limit:
                lines.append(current.rstrip())
                current = ''
                token = token.lstrip()
            for character in token:
                if current and _width(current + character) > limit:
                    lines.append(current.rstrip())
                    current = ''
                current += character
        lines.append(current.rstrip())
    return lines or ['']


def wrapped_text(value, x, y, width, size=24, line_height=None,
                 fill='#3b2673', weight=400):
    line_height = line_height or size * 1.4
    return '\n'.join(svg_text(line, x, y + i * line_height, size, fill, weight)
                     for i, line in enumerate(text_lines(value, width, size)))


def document(svg, language, title, filename, details_html=''):
    """Wrap a generated SVG in a self-contained, local-file-safe save page.

    The image contains only SVG shapes and native text, never foreignObject.
    Like levels/index.html, download uses canvas.toBlob and supplies a PNG
    preview for mobile browsers which choose not to honor the download link.
    """
    if language not in ('zh', 'en'):
        raise ValueError('lang must be zh or en')
    labels = ({'save': '存成图片', 'hint': '图片在本机生成。手机未下载时，可长按生成的图片保存。',
               'working': '正在生成图片…', 'done': '图片已生成。也可以点击下方链接，或长按图片保存。',
               'failed': '暂时无法生成图片，请重试或换一个浏览器。', 'link': '另存 PNG 图片',
               'preview': '生成的 PNG 图片'} if language == 'zh' else
              {'save': 'Save as image', 'hint': 'Created on your device. If it does not download on your phone, press and hold the generated image.',
               'working': 'Creating image…', 'done': 'Image created. You can also use the link below, or press and hold the image to save it.',
               'failed': 'Could not create the image. Please try again or use another browser.',
               'link': 'Save PNG image', 'preview': 'Generated PNG image'})
    out = ['<!doctype html>', '<html lang="{}"><head><meta charset="utf-8">'.format('zh-CN' if language == 'zh' else 'en'),
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src blob: data:; base-uri \'none\'; connect-src \'none\'">',
           '<title>{}</title>'.format(_xml(title)), '<style>',
           '*{box-sizing:border-box}body{margin:0;background:#f7f8fa;color:#0f1115;font-family:"Noto Sans SC","Source Han Sans SC","Microsoft YaHei",sans-serif}main{max-width:720px;margin:0 auto;padding:20px 16px 40px}html[lang=en] body{font-family:Inter,"Noto Sans","Segoe UI","Noto Sans SC","Microsoft YaHei",sans-serif}.card{border-radius:20px;overflow:hidden;box-shadow:0 12px 44px #3b267318}.card>svg{display:block;width:100%;height:auto}.tools{padding:22px 4px}button{background:#3b2673;color:white;border:0;border-radius:12px;padding:14px 22px;font:inherit;font-size:16px;font-weight:700;cursor:pointer}button:disabled{opacity:.6;cursor:wait}p{font-size:14px;line-height:1.6}#save-status img{display:block;max-width:100%;height:auto;margin-top:16px}#save-status a{display:block;margin-top:12px;color:#3b2673}',
           '</style></head><body><main><div class="card">', svg,
           '</div><div class="tools"><button id="save-image" type="button" data-filename="{}">{}</button>'.format(_xml(filename), _xml(labels['save'])),
           '<p>{}</p><div id="save-status" role="status" aria-live="polite" data-working="{}" data-done="{}" data-failed="{}" data-link="{}" data-preview="{}"></div></div>'.format(*(_xml(labels[key]) for key in ('hint', 'working', 'done', 'failed', 'link', 'preview'))),
           details_html, '</main>',
           '''<script>
'use strict';
(() => {
  const button = document.getElementById('save-image');
  const status = document.getElementById('save-status');
  button.addEventListener('click', async () => {
    button.disabled = true;
    status.textContent = status.dataset.working;
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    const source = document.querySelector('.card > svg');
    const svg = new XMLSerializer().serializeToString(source);
    const sourceURL = URL.createObjectURL(new Blob([svg], {type: 'image/svg+xml;charset=utf-8'}));
    const image = new Image();
    const fail = () => {
      URL.revokeObjectURL(sourceURL);
      button.disabled = false;
      status.textContent = status.dataset.failed;
    };
    image.onerror = fail;
    image.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const box = source.viewBox.baseVal;
        canvas.width = Math.ceil(box.width);
        canvas.height = Math.ceil(box.height);
        const context = canvas.getContext('2d');
        if (!context) { fail(); return; }
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(blob => {
          if (!blob) { fail(); return; }
          const url = URL.createObjectURL(blob);
          const download = document.createElement('a');
          download.href = url;
          download.download = button.dataset.filename;
          document.body.append(download);
          download.click();
          download.remove();
          const preview = document.createElement('img');
          preview.src = canvas.toDataURL('image/png');
          preview.alt = status.dataset.preview;
          const alternative = document.createElement('a');
          alternative.href = preview.src;
          alternative.download = button.dataset.filename;
          alternative.textContent = status.dataset.link;
          status.replaceChildren(document.createTextNode(status.dataset.done), alternative, preview);
          URL.revokeObjectURL(sourceURL);
          setTimeout(() => URL.revokeObjectURL(url), 30000);
          button.disabled = false;
        }, 'image/png');
      } catch (error) { fail(); }
    };
    image.src = sourceURL;
  });
})();
</script></body></html>''', '']
    return '\n'.join(out)
