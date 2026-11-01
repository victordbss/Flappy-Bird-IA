from itertools import count
import pygame
import neat
import os
import math
import sys
import random

generation = 0
best_score = 0

pygame.init()

# CONSTANTS
WIDTH, HEIGHT = 576, 1024
SCALE = 1
BACKGROUND_SPEED = 5

# BIRD CONSTANTS
GRAVITY = 0.8
JUMP_VEL = 10
MAX_VEL = 12

### GAME DIFFICULTY ###
PIPE_H = 0.3

# TIME BETWEEN PIPES
START_TIME_GAP = 100
FINAL_TIME_GAP = 35
FACTOR_TIME_GAP = 0.1

# PIPE GAP
START_GAP = 400
FINAL_GAP = 100
FACTOR_GAP = 0.1

# PIPES VELOCITY
START_VELOCITY = 6
FINAL_VELOCITY = 14
FACTOR_VELOCITY = 0.05


win = pygame.display.set_mode((
    int(WIDTH * SCALE),
    int(HEIGHT * SCALE)
))
game_surface = pygame.Surface((WIDTH, HEIGHT))

pygame.display.set_caption("Flappy Python")

radius = 15
wallW = 104

pipe_img = pygame.transform.scale2x(pygame.image.load(os.path.join("images","pipe-green.png")).convert_alpha())
bg_img = pygame.transform.scale(pygame.image.load(os.path.join("images","background-day.png")).convert_alpha(), (WIDTH, HEIGHT))
base_img = pygame.transform.scale(pygame.image.load(os.path.join("images","base.png")).convert_alpha(), (WIDTH, 100))
bird_images = [pygame.transform.scale2x(pygame.image.load(os.path.join("images","bird" + str(x) + ".png"))) for x in range(1,4)]



class Ball:
    def __init__(self, x : int = 100, y : int = HEIGHT // 2, radius : int = radius):
        self.x = x
        self.y = y
        self.radius = radius

        self.image = bird_images[0]
        self.count = 0
        self.y_vel = 0
        self.anim = 0
        self.isAlive = True
        self.reward = 0

    def move(self):
        if self.y_vel <= MAX_VEL:
            self.y_vel += GRAVITY
        self.y += self.y_vel


    def jump(self):
        self.y_vel = -JUMP_VEL
        self.anim = 10
        self.count = -1

    def animate(self):
        if self.anim >= 9:
            self.anim = 0
            if self.count < len(bird_images) - 1:
                self.count += 1
                self.image = bird_images[self.count]
            else:
                self.image = bird_images[1]
                self.count = -1
            
        else:
            self.anim +=1

    def collide(self, pipes_gen, genome):
        base = pygame.mask.from_surface(base_img)
        bird_mask = pygame.mask.from_surface(self.image)
        if bird_mask.overlap(base, (-self.x, HEIGHT - 100 - round(self.y))) or self.y < -2 * self.radius:
            self.isAlive = False
            genome[1].fitness -= 3

        for pipe in pipes_gen.pipes:
            up_mask = pygame.mask.from_surface(pipe.up_pipe_image)
            down_mask = pygame.mask.from_surface(pipe.down_pipe_image)
            top_offset = (pipe.x - self.x, pipe.h - pipe.gap // 2 - 640 - self.y)
            bottom_offset = (pipe.x - self.x, pipe.h + pipe.gap // 2 - self.y)

            b_point = bird_mask.overlap(down_mask, bottom_offset)
            t_point = bird_mask.overlap(up_mask, top_offset)

            if b_point or t_point:
                self.isAlive = False
                genome[1].fitness -= 3
        

    def draw(self, win):
        self.animate()
        rotated_image = pygame.transform.rotate(self.image, math.radians(-self.y_vel * 180))
        new_rect = rotated_image.get_rect(center = self.image.get_rect(topleft = (self.x, self.y)).center)
        win.blit(rotated_image, new_rect.topleft)


    def get_data(self, pipes_gen):

        next_pipe = None
        
        for pipe in pipes_gen.pipes:
            if pipe.x + wallW >= self.x:
                next_pipe = pipe
                break

        if next_pipe is None:
            return [self.y, self.y_vel, WIDTH, HEIGHT // 2, START_GAP]

        return [
            self.y,
            self.y_vel,
            next_pipe.x,
            next_pipe.h,
            next_pipe.gap
        ]

class Background:
    def __init__(self, x_bg : int = 0, x_base : int = 0):
        self.x_bg = x_bg
        self.x_base = x_base

    def move(self, base_speed : int):
        self.x_bg -= base_speed // 2.5
        if self.x_bg <= -576:
            self.x_bg = 0
        self.x_base -= base_speed // 1.5
        if self.x_base <= -576:
            self.x_base = 0
        

    def draw(self, win : pygame.display):
        win.blit(bg_img, (self.x_bg, 0))
        win.blit(bg_img, (self.x_bg + WIDTH, 0))
        win.blit(base_img, (self.x_base, HEIGHT-100))
        win.blit(base_img, (self.x_base + WIDTH, HEIGHT-100))

class Pipe:
    def __init__(self, x : int = WIDTH + wallW // 2, gap : int = 400, h : int = HEIGHT // 2, vel : int = 6):
        self.x = x
        self.gap = gap
        self.h = h
        self.vel = vel
        self.up_pipe_image = pygame.transform.rotate(pygame.transform.scale(pygame.image.load(os.path.join("images", "pipe-green.png")).convert_alpha(), (wallW, 640)), 180)
        self.down_pipe_image = pygame.transform.scale(pygame.image.load(os.path.join("images", "pipe-green.png")).convert_alpha(), (wallW, 640))


    def draw(self, win : pygame.display):
        win.blit(self.up_pipe_image, (self.x, self.h - (self.gap // 2) - 640))
        win.blit(self.down_pipe_image, (self.x, self.h + (self.gap // 2) ))

    def move(self):
        self.x -= self.vel

class PipeGeneration:
    def __init__(self, pipes: list[Pipe] = [], start_velocity : int = START_VELOCITY, time_gap : int = START_TIME_GAP, start_gap : int = START_GAP):
        self.pipes = pipes
        self.velocity = start_velocity
        self.time_gap = time_gap
        self.count = time_gap
        self.gap = start_gap
        self.pipe_counter = 0

    def generate_pipe(self):
        self.delete_pipe()

        if self.count >= self.time_gap:
            self.count = 0
            new_pipe = Pipe(vel=self.velocity, gap=self.gap, h = random.randint(int(HEIGHT * PIPE_H), int(HEIGHT * (1 - PIPE_H))))
            self.pipes.append(new_pipe)
            self.time_gap =  (START_TIME_GAP - FINAL_TIME_GAP) * math.exp(- FACTOR_TIME_GAP * self.pipe_counter) + FINAL_TIME_GAP
            self.gap = (START_GAP - FINAL_GAP) * math.exp(- FACTOR_GAP * self.pipe_counter) + FINAL_GAP
            self.velocity = - ((FINAL_VELOCITY - START_VELOCITY) * math.exp(- FACTOR_VELOCITY * self.pipe_counter) - FINAL_VELOCITY)

            self.pipe_counter += 1
        else:
            self.count += 1

    def delete_pipe(self):
        remove_pipe : list [Pipe] = []
        for pipe in self.pipes:
            if pipe.x <= - wallW:
                remove_pipe.append(pipe)

        for pipe in remove_pipe:
            self.pipes.remove(pipe)

    def draw_pipes(self, win : pygame.display):
        for pipe in self.pipes:
            pipe.draw(win)

    def move_pipes(self, balls_x):
        start = self.pipes[0].x > balls_x
        for pipe in self.pipes:
            pipe.move()
        end = self.pipes[0].x <= balls_x
        if start and end:
            return True
        else:
            return False

    
def gameLogic(balls : list [Ball], background : Background, pipes_gen : PipeGeneration, genomes, score):
    
    background.move(base_speed=pipes_gen.velocity)

    for i, ball in enumerate(balls):
        if ball.isAlive:
            ball.move()
            ball.collide(pipes_gen, genomes[i])
    pipes_gen.generate_pipe()
    if pipes_gen.move_pipes(balls[0].x):
        for i, ball in enumerate(balls):
            if ball.isAlive:
                genomes[i][1].fitness += 10
        score += 1

    return score



def update(clock):
    clock.tick(30)
    pygame.display.flip()

def draw(win : pygame.display, balls : list [Ball], background : Background, pipes_gen : PipeGeneration, generation : int, remain_balls : int, score : int, font):
    background.draw(game_surface)
    for ball in balls:
        if ball.isAlive:
            ball.draw(game_surface)
    pipes_gen.draw_pipes(game_surface)


    generation_text = font.render(
        f"Generation : {generation}",
        True,
        (255, 255, 255)
    )

    birds_text = font.render(
        f"Remain Birds : {remain_balls}",
        True,
        (255, 255, 255)
    )

    score_text = font.render(
        f"Score : {score}",
        True,
        (255, 255, 255)
    )
    best_score_text = font.render(
        f"Best score : {best_score}",
        True,
        (255, 255, 255)
    )

    game_surface.blit(generation_text, (20, 20))
    game_surface.blit(birds_text, (20, 60))
    game_surface.blit(score_text, (20, 100))
    game_surface.blit(best_score_text, (20, 140))

    scaled_surface = pygame.transform.scale(
        game_surface,
        win.get_size()
    )

    win.blit(scaled_surface, (0, 0))



def main(genomes, config):

    nets = []
    balls : list [Ball] = []

    for id, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0

        balls.append(Ball())



    gameStarted = False
    
    clock = pygame.time.Clock()

    bg = Background()
    pipes_gen = PipeGeneration()  
    pipes_gen.pipes = []  
    running = True

    generation_font = pygame.font.SysFont("Arial", 70)
    font = pygame.font.SysFont("Arial", 30)

    global generation
    generation += 1
    global best_score

    score = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
        
        keys = pygame.key.get_pressed()

        for index, ball in enumerate(balls):
            output = nets[index].activate(ball.get_data(pipes_gen))

            if output[0] > 0.5:
                ball.jump()
            

        remain_balls = 0
        for i, ball in enumerate(balls):
            if ball.isAlive:
                remain_balls += 1
                genomes[i][1].fitness += 0.1

        if remain_balls == 0:
            break


        score = gameLogic(balls, bg, pipes_gen, genomes, score)
        if score > best_score:
            best_score = score

        draw(win, balls, bg, pipes_gen, generation, remain_balls, score, font)

        

        update(clock)




if __name__ == "__main__":
    # Set configuration file
    config_path = "./neat-config.txt"
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, config_path)

    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    # Run NEAT
    p.run(main, 1000)
    pygame.quit()