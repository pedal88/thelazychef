from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
import xml.etree.ElementTree as etree

class VideoTreeprocessor(Treeprocessor):
    def run(self, root):
        for element in root.iter('img'):
            src = element.get('src')
            if src and (src.endswith('.mp4') or src.endswith('.mov') or src.endswith('.webm')):
                # Convert <img> to <video>
                element.tag = 'video'
                element.set('controls', 'true')
                element.set('playsinline', 'true')
                element.set('autoplay', 'true')
                element.set('muted', 'true')
                element.set('loop', 'true')
                element.set('class', 'w-full rounded-lg shadow-md my-4') # Tailwind classes
                # Remove 'alt' if presents, as video doesn't use it the same way (or keep it?)
                # Video doesn't use alt attribute standardly, but we can leave it or remove it.
                if 'alt' in element.attrib:
                    del element.attrib['alt']

class VideoExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(VideoTreeprocessor(md), 'video_extension', 15)

def make_extension(**kwargs):
    return VideoExtension(**kwargs)
