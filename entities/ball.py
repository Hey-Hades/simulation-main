import pygame
import pymunk

class Ball :
    def __init__(self ,space , x , y , color):
        self.radius = 20
        self.color = color

        mass = 1

        moment = pymunk.moment_for_circle(
                mass,
                0,
                self.radius
                )

        self.body = pymunk.Body(mass,moment)
        
        self.body.position(x,y)

        self.shape = pymunk.Circle(self.body,self.radius)
        
        self.shape.elasticity = 0.95

        space.add(self.body,self.shape)

    def draw(self,screen,camera):
        a = int(self.body.position.x + camera.x)
        b = int(self.body.position.y + camera.y)

        pygame.draw.circle(screen,(40,40,80),(x,y),self.radius + 8)

        

