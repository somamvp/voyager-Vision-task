# RGB+D 이미지를 RGBA 포맷에 맞춰서 보내도록 한다

from PIL import Image

image_file = Image.open("./MP_SEL_000066.jpg").convert('RGB')
image_file.save('converted.webp','webp')
