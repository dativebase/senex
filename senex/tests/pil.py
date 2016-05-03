import Image

im = Image.open('/home/joel/senex/senex/media/sample.jpg')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('/home/joel/senex/senex/media/small_sample.jpg')

im = Image.open('/home/joel/senex/senex/media/sample.png')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('/home/joel/senex/senex/media/small_sample.png')

im = Image.open('/home/joel/senex/senex/media/sample.gif')
im.thumbnail((200, 200), Image.ANTIALIAS)
im.save('/home/joel/senex/senex/media/small_sample.gif')