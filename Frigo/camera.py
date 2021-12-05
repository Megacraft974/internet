import pygame
from pyzbar.pyzbar import decode
from time import sleep
from platform import system
if system() == 'Windows':
    import cv2
else:
    pass
import numpy as np
import os

DEVICE = 1
SIZE = (640, 480)
SIZE = (int(1280/2),int(960/2))
FILENAME = 'capture.png'

"""pygame.init()
display = pygame.display.set_mode((SIZE[0],SIZE[1]), 0)
pos = (0,0)"""

class getBarCode:
    def __init__(self,display,pos,camSize,size,device):
        self.device=device
        self.screen = pygame.surface.Surface(size, 0, display)

        self.display=display
        self.pos=pos
        self.size=size

        if system() == 'Windows':
            self.cap = cv2.VideoCapture(self.device)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camSize[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camSize[1])

        print("Scanner ready!")
    def get(self):
        _, self.npscreen = self.cap.read()

        self.image = cv2.transpose(self.npscreen)
        self.image = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
        self.screen = pygame.surfarray.make_surface(self.image)
        
        targetSize = self.screen.get_rect().fit((0,0),self.size)
        self.pos = (self.pos[0],self.pos[1]+((self.size[1]-targetSize[3])/2))
        self.size = targetSize[-2:]
        self.screen = pygame.transform.scale(self.screen, self.size)
        
        self.d=decode(self.npscreen)
        if self.d!=[]:
            print("Barcode detected, ending")
            pygame.draw.rect(self.screen,(0,255,0),(0,0,self.size[0],self.size[1]),15)
            self.display.blit(self.screen, self.pos)
            #pygame.display.flip()
            #sleep(0.5)
            return self.d[0][0].decode('ascii')


        self.display.blit(self.screen, self.pos)
        #pygame.display.flip()
        
        #print("Screen updated")

    def picMode(self):
        _, self.npscreen = self.cap.read()
        
        self.image = cv2.transpose(self.npscreen)
        self.image = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
        self.screen = pygame.surfarray.make_surface(self.image)
        
        targetSize = self.screen.get_rect().fit((0,0),self.size)
        self.pos = (self.pos[0],self.pos[1]+((self.size[1]-targetSize[3])/2))
        self.size = targetSize[-2:]
        self.screen = pygame.transform.scale(self.screen, self.size)

        self.display.blit(self.screen, self.pos)

    def shoot(self):
        _, pic = self.cap.read()
        img = cv2.resize(pic,(int(self.size[0]/2),int(self.size[1]/2)))
        _, img = cv2.imencode('.png',img)
        file = open(FILENAME, 'wb')
        file.write(img)
        file.close()
        return img

if __name__ == '__main__':
    scanner=getBarCode(display,pos,SIZE,SIZE,DEVICE)
    out = None
    while out == None:
        out=scanner.get()
        pygame.display.update()
    print(out)
    pygame.quit()
