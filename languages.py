import pygame
import sys
import random

# Inicjalizacja Pygame
pygame.init()

# Ustawienia ekranu
width = 800
height = 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pong - AI")

# Kolory
white = (255, 255, 255)
black = (0, 0, 0)

# Inicjalizacja pasków i piłki
left_paddle = pygame.Rect(20, height // 2 - 50, 10, 100)
right_paddle = pygame.Rect(width - 30, height // 2 - 50, 10, 100)
ball = pygame.Rect(width // 2 - 10, height // 2 - 10, 20, 20)

# Prędkość ruchu (zmniejszona do 4 zamiast 7)
dx = 4 * random.choice((1, -1))
dy = 4 * random.choice((1, -1))

# Punkty
left_score = 0
right_score = 0

# Czcionka
font = pygame.font.SysFont("Arial", 32)


def reset_ball():
    global dx, dy
    ball.center = (width // 2, height // 2)
    dx = 4 * random.choice((1, -1))  # Nowa prędkość
    dy = 4 * random.choice((1, -1))
    pygame.time.delay(1000)  # Opóźnienie przed ponownym uruchomieniem


# Główna pętla gry
clock = pygame.time.Clock()
while True:
    screen.fill(black)

    # Obsługa zdarzeń
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    # Ruch paletki (gracz 1: W/S, AI: automatycznie)
    keys = pygame.key.get_pressed()

    # Gracz 1 - lewa paleta (W/S)
    if keys[pygame.K_w] and left_paddle.top > 0:
        left_paddle.y -= 8
    if keys[pygame.K_s] and left_paddle.bottom < height:
        left_paddle.y += 8

    # AI - prawa paleta
    ai_speed = 5
    if right_paddle.centery < ball.centery:
        right_paddle.y += ai_speed
    elif right_paddle.centery > ball.centery:
        right_paddle.y -= ai_speed

    # Ograniczenie ruchu AI do ekranu
    right_paddle.y = max(0, min(right_paddle.y, height - right_paddle.height))

    # Ruch piłki
    ball.x += dx
    ball.y += dy

    # Odbicie od górnej i dolnej ściany
    if ball.top <= 0 or ball.bottom >= height:
        dy *= -1

    # Odbicie od paletki
    if ball.colliderect(left_paddle) or ball.colliderect(right_paddle):
        dx *= -1

    # Sprawdzenie punktów
    if ball.left < 0:
        right_score += 1
        reset_ball()
    elif ball.right > width:
        left_score += 1
        reset_ball()

    # Rysowanie elementów
    pygame.draw.rect(screen, white, left_paddle)
    pygame.draw.rect(screen, white, right_paddle)
    pygame.draw.ellipse(screen, white, ball)

    # Wyświetlanie punktów
    left_text = font.render(str(left_score), True, white)
    right_text = font.render(str(right_score), True, white)
    screen.blit(left_text, (350, 20))
    screen.blit(right_text, (410, 20))

    pygame.display.flip()
    clock.tick(60)
