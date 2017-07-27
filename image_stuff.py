import abc
from PIL import Image
from functools import *

class RenderItem:
    @abc.abstractmethod
    def getWidth(self):
        pass

    @abc.abstractmethod
    def getHeight(self):
        pass

    @abc.abstractmethod
    def render(self, image, position):
        pass

def itemswidth(items,GAP_horizontal):
    return reduce(lambda x,y: x + GAP_horizontal + y,
            map(lambda renderitem: renderitem.getWidth(),
                items))

def itemsheight(items):
    return reduce(max, map(lambda renderitem: renderitem.getHeight(), items))

class Picture(RenderItem):
    def __init__(self, image):
        self.image = Image.open("covers/"+image)

    def getWidth(self):
        return self.image.width

    def getHeight(self):
        return self.image.height

    def render(self, image, position):
        image.paste(self.image, position)

class ResizePicture(Picture):
	def __init__(self, image, newsize):
		Picture.__init__(self, image)
		self.image = self.image.resize(newsize)

class Label(Picture):
	def __init__(self, image):
		Picture.__init__(self, image)


class Bind(RenderItem):
    def __init__(self, first, second, gap):
        self.first = first
        self.second = second
        self.gap = gap

    def getWidth(self):
        return self.first.getWidth() + self.gap + self.second.getWidth()

    def getHeight(self):
        return max(self.first.getHeight(), self.second.getHeight())

    def render(self, image, position):
        self.first.render(image,
            (position[0],
                position[1] + int((self.getHeight() - self.first.getHeight()) / 2)))
        self.second.render(image,
            (position[0] + self.first.getWidth() + self.gap,
                position[1] + int((self.getHeight() - self.second.getHeight()) / 2)))

    def recFirst(self):
        if type(self.first) is Bind:
            return self.first.recFirst()
        else:
            return self.first

    def recSecond(self):
        if type(self.second) is Bind:
            return self.second.recSecond
        else:
            return self.second
