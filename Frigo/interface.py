# coding: utf-8
from tkinter import *
import pygame
import requests
import json
import os
from math import pi
from time import time,localtime
from calendar import monthrange
import datetime
import platform

import camera

def drawRoundedRectangle(surface, color, rect, radius):
    x1,y1,x2,y2=rect
    pygame.draw.rect(surface,color,(x1+radius,y1,x2-(radius*2),y2))
    pygame.draw.rect(surface,color,(x1,y1+radius,x2,y2-(radius*2)))
    pygame.draw.circle(surface,color,(x1+radius,y1+radius),radius)
    pygame.draw.circle(surface,color,(x1+x2-radius,y1+radius),radius)
    pygame.draw.circle(surface,color,(x1+radius,y1+y2-radius),radius)
    pygame.draw.circle(surface,color,(x1+x2-radius,y1+y2-radius),radius)
    return pygame.Rect(rect)

class interfacePygame:
    def __init__(self):
        self.path = os.getcwd()
        self.os = platform.system()
        print(self.os)

        self.fenSize = (800, 480)
        self.sideBarWidth = 70
        self.screenSize = (self.fenSize[0]-self.sideBarWidth, self.fenSize[1])

        pygame.init()
        if self.os == 'Linux':
            pygame.mouse.set_cursor((8,8),(0,0),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))
            self.mainSpace = pygame.display.set_mode(self.fenSize, pygame.NOFRAME)
        else:
            self.mainSpace = pygame.display.set_mode(self.fenSize)
        self.screen = pygame.Surface(self.screenSize)

        self.scannerSize=(self.screenSize[0]/2-20,self.screenSize[0]/2-20)
        #self.scanner=camera.getBarCode(self.screen,(self.scannerSize[0],(self.screenSize[1]-self.scannerSize[0])/2),(640, 480),self.scannerSize,1)
        
        self.running = True
        
        self.needUpdate = True
        self.scrolling = False
        self.lastTick = localtime().tm_sec
        self.tickState = True
        self.date = datetime.datetime.now()
        self.updateNotifRate = 30
        self.lastNotifUpdate = -self.updateNotifRate
        self.notifData = []
        self.notifDataDesc = []
        self.notifOffset = 0
        self.binTypes = {'E':'Encombrants','M':'Poubelle verte','R':'Poubelle jaune','V':'Végétaux'}
        self.planning=None
        self.rctIds = []
        self.recetteId = None
        self.recetteOffset = 0
        self.state="main"
        self.butClicked=0

        self.barcode=12345
        self.urlAdd = 'http://patrice.atwebpages.com/frigo/index.php?page=addRef&&vals='
        self.urlRemove = 'http://patrice.atwebpages.com/frigo/index.php?page=delRef&&vals='
        self.urlPic = 'http://patrice.atwebpages.com/frigo/index.php?page=addImg'
        self.urlBinMonth = 'http://patrice.atwebpages.com/frigo/index.php?page=getPoubMois&&modeApi&&mois={}&&annee={}'
        self.urlBinTomorrow = 'http://patrice.atwebpages.com/frigo/index.php?page=getPoubDemain&&modeApi=true'

        self.buttonsRect = []
        self.buttonActions = [self.drawMain,self.drawFrigo,self.drawBin,self.drawRDV,self.drawRecettes,self.drawSettings]
        
        self.drawMainBar()
        self.drawMain()

        while self.running:
            #_________________________________________Events/Input___________________________________________
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEMOTION:
                    if event.buttons[0] == 1:
                        self.scrolling = True
                        if self.state == "main":
                            if scroll_mouse_pos == None:
                                scroll_mouse_pos = (event.pos[0]-576,event.pos[1])
                            if self.notifScreen.get_rect().collidepoint(scroll_mouse_pos):
                                #print(mouse_pos[1]-event.pos[1])
                                self.notifOffset += event.rel[1]
                            #print(scroll_mouse_pos,self.notifScreen.get_rect())
                        elif self.state == "Recettes":
                            self.recetteOffset += event.rel[1]
                            self.needUpdate = True
                    else:
                        self.scrolling = False
                        scroll_mouse_pos = None
                elif event.type == pygame.MOUSEBUTTONUP and self.scrolling == False:
                    mouse_pos = event.pos
                    for index,button in enumerate(self.buttonsRect):
                        if button.collidepoint(mouse_pos):
                            self.butClicked = index
                            print('Button x:{} y:{} was pressed at {}, index {}'.format(button.x,button.y,mouse_pos,self.butClicked))
                            self.screen.fill((38,40,42))
                            self.buttonActions[self.butClicked]()
                            self.needUpdate = True

                            if self.butClicked == 4: #Resetting the recette menu
                                self.recetteId = None
                    
                    screen_mouse_pos = (mouse_pos[0]-self.sideBarWidth,mouse_pos[1])
                    #print(mouse_pos)
                    
                    if self.state == "frigo" or self.state == "FrigoIn" or self.state == "FrigoOut":
                        if self.FrigoIn.collidepoint(screen_mouse_pos):
                            print("In")
                            self.state="FrigoIn"
                            self.butClicked=1
                            #self.Fill()
                        if self.FrigoOut.collidepoint(screen_mouse_pos):
                            print("Out")
                            self.state="FrigoOut"
                            self.butClicked=1
                            #self.Empty()
                            
                    elif self.state == "poubelles":
                        for b in self.calendarButtons:
                            if b.collidepoint(screen_mouse_pos):
                                self.date=datetime.datetime(int(self.date.strftime("%Y")),int(self.date.strftime("%m")),self.calendarButtons.index(b)+1)
                                #self.drawBin()
                        if self.binBack.collidepoint(screen_mouse_pos):
                            if int(self.date.strftime("%m"))-1 == 0:
                                backMonth=12
                                backYear=int(self.date.strftime("%Y"))-1
                            else:
                                backMonth=int(self.date.strftime("%m"))-1
                                backYear=int(self.date.strftime("%Y"))
                            self.date=datetime.datetime(backYear,backMonth,1)
                            self.planning = None
                        if self.binNext.collidepoint(screen_mouse_pos):
                            if int(self.date.strftime("%m"))+1 == 13:
                                nextMonth=1
                                nextYear=int(self.date.strftime("%Y"))+1
                            else:
                                nextMonth=int(self.date.strftime("%m"))+1
                                nextYear=int(self.date.strftime("%Y"))
                            self.date=datetime.datetime(nextYear,nextMonth,1)
                            self.planning = None
                            
                    elif self.state == "Recettes":
                        sensitivity=20
                        if self.rctUp.collidepoint(screen_mouse_pos):
                            self.recetteOffset += sensitivity
                            self.needUpdate = True
                        elif self.rctDown.collidepoint(screen_mouse_pos):
                            self.recetteOffset -= sensitivity
                            self.needUpdate = True
                        else:
                            if self.recetteId != None:
                                if self.rctBack.collidepoint(screen_mouse_pos):
                                    self.recetteId = None
                                    self.needUpdate = True
                            else:
                                for b in range(len(self.rctButtons)):
                                    if self.rctButtons[b].collidepoint(screen_mouse_pos):
                                        self.recetteId = self.rctIds[b]
                                        self.recetteOffset = 0
                                        self.needUpdate = True
                                        print(self.recetteId)
                                        break
                        
                    elif self.state == "Settings":
                        if self.buttonOff.collidepoint(screen_mouse_pos):
                            print("Shutdown")
                            self.shutdown()
                        elif self.buttonReboot.collidepoint(screen_mouse_pos):
                            print("Reboot")
                            self.reboot()
                        elif self.buttonQuit.collidepoint(screen_mouse_pos):
                            print("Quit")
                            self.quit()
                        
            #_______________________________________Main loop_________________________________________________
            self.buttonActions[self.butClicked]()
            if self.needUpdate:
                self.needUpdate=False
                self.mainSpace.blit(self.screen,(self.sideBarWidth,0))
                pygame.display.update()
                self.drawMainBar()
        pygame.display.quit()

    def drawMainBar(self):
        self.screen.fill((38,40,42))
        self.mainSpace.fill((38,40,42))
        pygame.draw.rect(self.mainSpace,(50,50,52),(0,0,self.sideBarWidth,self.fenSize[1]))

        buttonContent=["home","cart","delete","calendar","copy","settings"]

        bOffX, bOffY = 5,10
        bSizeX = bSizeY = 60

        imgSize = 24
        imgOff = (bSizeY/2)-(imgSize/2)
        
        self.buttonsRect = []
        for i in range(len(buttonContent)):
            self.buttonsRect.append(pygame.draw.rect(self.mainSpace, (71,71,73), (bOffX, bOffX +(bOffY+bSizeX)*i,bSizeX,bSizeY)))
            img = pygame.image.load(self.path+"/Ui/"+buttonContent[i]+".png")
            self.mainSpace.blit(img,(bOffX + imgOff, bOffX +(bOffY+bSizeX)*i + imgOff))
        
        #self.mainSpace.blit(self.screen,(self.sideBarWidth,0))

    def drawMain(self):
        #print(str(self.tickState)+"-"+str(localtime().tm_sec)+"-"+str(self.lastTick+1))
        self.state="main"

        #Clock
        if self.lastTick != localtime().tm_sec:
            self.lastTick = localtime().tm_sec
            self.tickState = not self.tickState
        if self.tickState:
            tick=":"
        else:
            tick=" "
        time = str(localtime().tm_hour).zfill(2)+tick+str(localtime().tm_min).zfill(2)
        font = pygame.font.Font(self.path+"/Ui/digital-7 (mono).ttf", 125)

        clockRender = font.render(time, 1, (71, 71, 73))
        
        clockPos=(self.screenSize[0]/2-clockRender.get_width()/2-50,self.screenSize[1]/2-clockRender.get_height()/2)
        updateMargin=100
        updateMarginSize=(clockPos[0]+(updateMargin/2),clockPos[1])
        
        self.screen.fill((38,40,42),clockRender.get_rect().move(updateMarginSize).inflate(updateMargin,0))
        self.screen.blit(clockRender, clockPos)

        #Notifs
        notifBorderSize=(20,10)
        notifCellSize=(int(self.screenSize[0]/2),75)
        notifPos=(0,15)
        notifScreenSize=(self.screenSize[0]/2,40+(len(self.notifData)*notifCellSize[1]))
        notifScreenPosX=self.screenSize[0]/2
        
        self.notifScreen = pygame.Surface(notifScreenSize)
        self.notifScreen.fill((38,40,42))
            
        if -self.notifOffset > ((notifPos[1])+(len(self.notifData)*notifCellSize[1])-self.screenSize[1]):
            self.notifOffset = -((notifPos[1])+(len(self.notifData)*notifCellSize[1])-self.screenSize[1])
        elif self.notifOffset > 0:
            self.notifOffset = 0
            
        for n in range(len(self.notifData)):
            print(n)
            drawRoundedRectangle(self.notifScreen, (0, 255, 0), (notifPos[0],notifPos[1]+(n*notifCellSize[1]),notifCellSize[0]-notifBorderSize[0],notifCellSize[1]-notifBorderSize[1]), 10)
            notifTextRender = pygame.font.Font(None, 50).render(self.notifData[n], 1, (38,40,42))
            self.notifScreen.blit(notifTextRender, (5+notifPos[0],notifPos[1]+(n*notifCellSize[1])))
            notifDescTextRender = pygame.font.Font(None, 40).render(self.notifDataDesc[n], 1, (38,40,42))
            self.notifScreen.blit(notifDescTextRender, (10+notifPos[0],35+notifPos[1]+(n*notifCellSize[1])))

        if self.lastNotifUpdate + self.updateNotifRate >= 60:
            self.lastNotifUpdate = 60 - self.lastNotifUpdate + self.updateNotifRate
            
        if localtime().tm_min >= self.lastNotifUpdate + self.updateNotifRate:
            self.updateNotifs()
            self.lastNotifUpdate = localtime().tm_min

        #Update
        self.screen.blit(self.notifScreen,(notifScreenPosX,0))
        self.mainSpace.blit(self.screen,(self.sideBarWidth,0))
        pygame.display.update()

    def updateNotifs(self):
        b = self.getTomorrowBin()
        if not 'inconnu' in b:
            self.notifData.append("Prochaine poubelle")
            self.notifDataDesc.append(self.binTypes[b['type_collecte']])
        else:
            print('Pas de poubelle demain')
        

    #______________________________________Frigo_____________________________________
    def drawFrigo(self):
        if not self.state == "FrigoIn" and not self.state == "FrigoOut" and not self.state == "FrigoUnknown":
            self.state="frigo"

        
        bOffX,bOffY= 100,self.screenSize[1]/4
        bSpace = bOffY
        bSizeX,bSizeY = 200,50

        FrigoButtons=[(bOffX,bOffY,bSizeX,bSizeY),(bOffX,bOffY+bSizeY+bSpace,bSizeX,bSizeY)]
        
        pygame.draw.rect(self.screen, (71,71,73), FrigoButtons[0])
        textRender = pygame.font.Font(None, 75).render("Remplir", 1, (38,40,42))
        self.screen.blit(textRender, (bOffX,bOffY))

        pygame.draw.rect(self.screen, (71,71,73), FrigoButtons[1])
        textRender = pygame.font.Font(None, 75).render("Vider", 1, (38,40,42))
        self.screen.blit(textRender, (bOffX,bOffY+bSizeY+bSpace))

        self.FrigoIn = pygame.Rect(FrigoButtons[0])
        self.FrigoOut = pygame.Rect(FrigoButtons[1])

        if self.state == "FrigoIn":
            pygame.draw.rect(self.screen, (69,161,255), FrigoButtons[0], 1)
        elif self.state == "FrigoOut":
            pygame.draw.rect(self.screen, (69,161,255), FrigoButtons[1], 1)
        
        #Camera stuff
        if self.state == "FrigoIn" or self.state == "FrigoOut":
            self.mainSpace.blit(self.screen,(self.sideBarWidth,0))
            out=self.scanner.get()
            pygame.display.update()
            if out != None:
                self.barcode=out
                if self.state == "FrigoIn":
                    self.Fill()
                elif self.state == "FrigoOut":
                    self.Empty()

        if self.state=="FrigoUnknown":
            textPos=self.screenSize[0]/2
            textRender = pygame.font.Font(None, 50).render("Article inconnu!", 1, (71,71,73))
            self.screen.blit(textRender, (textPos-(textRender.get_width()/2),15))
            textRender = pygame.font.Font(None, 50).render("Merci de prendre une photo.", 1, (71,71,73))
            self.screen.blit(textRender, (textPos-(textRender.get_width()/2),50))
            self.screen.fill((38,40,42),(650,525,50,50))
            textRender = pygame.font.Font(None, 50).render(str(3-(int(time())-self.counterStart)), 1, (71,71,73))
            self.screen.blit(textRender, (textPos-(textRender.get_width()/2),self.screenSize[1]-(textRender.get_height()*2)))
            
            self.mainSpace.blit(self.screen,(self.sideBarWidth,0))
            self.scanner.picMode()
            #pygame.display.update()
            self.needUpdate=True

            if 3-(int(time())-self.counterStart) <= 0:
                self.scanner.shoot()
                self.sendPic()
                self.state="FrigoIn"
                self.needUpdate=True

    def Fill(self):
        self.sendBarCode()

    def Empty(self):
        p = json.loads(requests.get(self.urlRemove+str(self.barcode)).text)
        print(p)
        
    def sendBarCode(self):
        p = requests.get(self.urlAdd+str(self.barcode))
        print(p.text)
        p = json.loads(p.text)
        if p["categorie"] == "inconnu":
            print(str(self.barcode) + " est inconnu. Affichage du formulaire?")
            self.state="FrigoUnknown"
            self.counterStart = int(time())

    def sendPic(self):
        file = {self.barcode:open(self.path+"/capture.png","rb").read()}
        r = requests.post(self.urlPic,data=file,auth=('3482246_pat', 'pat/Pat/974'))
        print(r.text)


    #______________________________________Poubelles_____________________________________
    def drawBin(self):
        self.state = "poubelles"
        year=self.date.strftime("%Y")
        month=self.date.strftime("%m")
        day=self.date.strftime("%d")

        if self.planning == None:
            self.planning = self.getMonthBin()
            for i in self.planning:
                self.planning[self.planning.index(i)]['date_collecte']=datetime.datetime.strptime(i['date_collecte'], '%Y-%m-%d')
                #print(self.planning[self.planning.index(i)]['date_collecte'].strftime("%x")+": "+i['type_collecte'])

        for d in self.planning:
            if int(self.date.strftime("%d")) == int(d['date_collecte'].strftime("%d")):
                self.binType=self.binTypes[d['type_collecte']]
                break
            else:
                self.binType="Pas de collecte"

        monthNames = ['Janvier','Fevrier','Mars','Avril','Mai','Juin','Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
        dateTextRender = pygame.font.Font(None, 90).render(str(day)+" "+monthNames[int(month)-1]+" "+str(year), 1, (71,71,73))
        self.screen.blit(dateTextRender, (self.screenSize[0]/2-(dateTextRender.get_width()/2),30)) 
        typeTextRender = pygame.font.Font(None, 60).render(self.binType, 1, (71,71,73))
        self.screen.blit(typeTextRender, (self.screenSize[0]/2-(typeTextRender.get_width()/2),100))

        #self.pastMonthBin = pygame.draw.rect(self.screen, (71,71,73), (50, 50, 25, 25))
        imgL = pygame.image.load(self.path+"/Ui/arrow (2).png")
        imgR = pygame.transform.flip(imgL,True,False)
        self.binBack = self.screen.blit(imgL,(50, 50))
        self.binNext = self.screen.blit(imgR,(self.screenSize[0]-50-imgR.get_width(), 50))
        
        font=pygame.font.Font(None, 50)
        if monthrange(int(year), int(month))[1] == 28:
            rows=4
        else:
            rows=5
        column=7
        tileYOffset = 175
        tileSize = (int(self.screenSize[0]/column),int((self.screenSize[1]-tileYOffset)/rows))
        self.calendarButtons=[]
        
        for y in range(rows):
            for x in range(column):
                if y*column+x+1 == int(day):
                    colour=(69,161,255)
                elif y*column+x+1 > monthrange(int(year), int(month))[1]:
                    break
                else:
                    colour=(71,71,73)
                
                fillcolour=(38,40,42)
                for d in self.planning:
                    if int(y*column+x+1) == int(d['date_collecte'].strftime("%d")):
                        colours={'E':(249,176,0),'M':(97,184,124),'R':(255,237,0),'V':(143,130,74)}
                        fillcolour=colours[d['type_collecte']]
                pygame.draw.rect(self.screen, fillcolour, (x*tileSize[0],tileYOffset+(y*tileSize[1]),tileSize[0],tileSize[1]))
                b = pygame.draw.rect(self.screen, colour, (x*tileSize[0],tileYOffset+(y*tileSize[1]),tileSize[0],tileSize[1]),1)
                self.calendarButtons.append(b)
                numTextRender = font.render(str(y*column+x+1), 1, colour)
                self.screen.blit(numTextRender, (x*tileSize[0]+5,tileYOffset+(y*tileSize[1])+3))

        self.needUpdate=True

    def getTomorrowBin(self):
        r = requests.get(self.urlBinTomorrow)
        if r.status_code == 200:
            return json.loads(r.text)

    def getMonthBin(self):
        r = requests.get(self.urlBinMonth.format(self.date.strftime("%m"),self.date.strftime("%Y")))
        if r.status_code == 200:
            return json.loads(r.text)

    def drawGrid(self):
        lines = []
        for x in range(0,924,50):
            lines.append((x,0))
            lines.append((x,600))
            lines.append((x,0))
        
        for y in range(0,600,50):
            lines.append((0,y))
            lines.append((924,y))
            lines.append((0,y))
                
        pygame.draw.lines(self.screen, (71,71,73), False, lines)

    #______________________________________RDV_____________________________________
    def drawRDV(self):
        self.state="RDV"
        textRender = pygame.font.Font(None, 75).render("Rendez-vous", 1, (71,71,73))
        self.screen.blit(textRender, (50,50))
        self.drawGrid()

    #______________________________________Recettes_____________________________________
    def drawRecettes(self):
        self.state="Recettes"
        self.rctButtons=[]
        rctUpDownPos = (100,20)
        rctTileOffset = 10
        rctTilePos = (20,20)
        rctTileSize = (self.screenSize[0]-rctTilePos[0],40)
        rctTilesYSize = rctTilePos[1]+((rctTileSize[1]+rctTileOffset)*len(self.rctIds))

        if self.rctIds == []:
            self.rctIds = os.listdir('Recettes/')
            self.rctIds+=self.rctIds
            self.rctIds+=self.rctIds
            for r in range(len(self.rctIds)):
                self.rctIds[r] = os.path.splitext(self.rctIds[r])[0]
                print(self.rctIds[r])
        
        if self.recetteId == None:
            self.screen.fill((38,40,42))
            if -self.recetteOffset > rctTilesYSize-self.screenSize[1]:
                self.recetteOffset = -(rctTilesYSize-self.screenSize[1])
                print(self.recetteOffset)
            elif self.recetteOffset > 0:
                self.recetteOffset = 0

            for r in range(len(self.rctIds)):
                out=''
                for l in self.rctIds[r]:
                    if l.isupper():
                        out += ' '
                    out += l.lower()
                out=out[1].upper()+out[2:]
                
                self.rctButtons.append(drawRoundedRectangle(self.screen, (71,71,73), (rctTilePos[0],rctTilePos[1]+self.recetteOffset+((rctTileSize[1]+rctTileOffset)*r),rctTileSize[0],rctTileSize[1]),10))
                textRender = pygame.font.Font(None, 50).render(out, 1, (38,40,42))
                self.screen.blit(textRender, (5+rctTilePos[0],3+rctTilePos[1]+self.recetteOffset+(rctTileSize[1]+rctTileOffset)*r))
            imgUpDown = pygame.image.load(self.path+"/Ui/arrow (2).png")
            imgUp = pygame.transform.rotate(imgUpDown,-90)
            imgDown = pygame.transform.rotate(imgUpDown,90)
            self.rctUp = self.screen.blit(imgUp,(self.screenSize[0]-rctUpDownPos[0], rctUpDownPos[1]))
            self.rctDown = self.screen.blit(imgDown,(self.screenSize[0]-rctUpDownPos[0], self.screenSize[1]-rctUpDownPos[1]-imgDown.get_height()))
        else:
            #Affichage
            rctRect = pygame.image.load(self.path+"/Recettes/"+self.recetteId+".JPG")
            tgtSize = rctRect.get_rect().fit((0,0,self.screenSize[0],rctRect.get_height()))
            rctRect = pygame.transform.scale(rctRect, tgtSize.size)

            if -self.recetteOffset > tgtSize.height-self.screenSize[1]:
                self.recetteOffset = self.screenSize[1]-tgtSize.height
            elif self.recetteOffset > 0:
                self.recetteOffset = 0
            self.screen.blit(rctRect,(0, 0 + self.recetteOffset))
            
            imgBack = pygame.image.load(self.path+"/Ui/arrow (2).png")
            self.rctBack = self.screen.blit(imgBack,(50, 50))
            imgUpDown = pygame.image.load(self.path+"/Ui/arrow (2).png")
            imgUp = pygame.transform.rotate(imgUpDown,-90)
            imgDown = pygame.transform.rotate(imgUpDown,90)
            self.rctUp = self.screen.blit(imgUp,(self.screenSize[0]-rctUpDownPos[0], rctUpDownPos[1]))
            self.rctDown = self.screen.blit(imgDown,(self.screenSize[0]-rctUpDownPos[0], self.screenSize[1]-rctUpDownPos[1]-imgDown.get_height()))
        
            #self.needUpdate=True
        

    #______________________________________Reglages_____________________________________
    def drawSettings(self):
        self.state="Settings"
        textRender = pygame.font.Font(None, 75).render("Réglages", 1, (71,71,73))
        self.screen.blit(textRender, (self.screenSize[0]/2-(textRender.get_width()/2),30))

        bSizeX = 50
        bSizeY = bSizeX

        imgOff = pygame.image.load(self.path+"/Ui/off.png")
        self.buttonOff = self.screen.blit(imgOff,(50,50))

        imgRb = pygame.image.load(self.path+"/Ui/reboot.png")
        self.buttonReboot = self.screen.blit(imgRb,(50,150))

        imgQuit = pygame.image.load(self.path+"/Ui/quit.png")
        self.buttonQuit = self.screen.blit(imgQuit,(50,250))

    def shutdown(self):
        self.running = False
        pygame.quit()
        if self.os == 'Windows':
            print('Not going down')
            return
        os.system('sudo shutdown -h now')
        
    def reboot(self):
        self.running = False
        pygame.quit()
        if self.os == 'Windows':
            print('Not rebooting')
            return
        os.system('sudo reboot')
        
    def quit(self):
        self.running = False
        try:
            pygame.quit()
        except:
            raise "Cannot quit the application"
        return

interfacePygame()
