import os
import logging
import functools
from PIL import Image, ImageTk, ImageDraw, ImageFont, UnidentifiedImageError
from .constants import (
    IMAGES_FOLDER,
    THUMBNAIL_FOLDER,
    RESAMPLING,
    DEFAULT_TILE_WIDTH,
    DEFAULT_TILE_HEIGHT,
)


@functools.lru_cache(maxsize=128)  # Cache dla domyślnych okładek
def create_default_cover(game_name, size=(DEFAULT_TILE_WIDTH, DEFAULT_TILE_HEIGHT)):
    """
    Tworzy prosty obrazek okładki z nazwą gry, jeśli okładka nie istnieje.
    Zapisuje obraz w folderze IMAGES_FOLDER.
    """
    image_path = os.path.join(
        IMAGES_FOLDER, f"{game_name}_default_cover.png"
    )  # Unikalna nazwa dla domyślnej

    # Sprawdź, czy domyślna okładka już istnieje
    if os.path.exists(image_path):
        return image_path

    logging.info(f"Tworzenie domyślnej okładki dla: {game_name}")
    image = Image.new("RGB", size, color="#2e2e2e")  # Ciemniejsze tło
    draw = ImageDraw.Draw(image)

    try:
        # Próba użycia czcionki systemowej
        font_path = "arial.ttf"
        max_font_size = int(size[1] / 6)  # Dostosuj rozmiar do wysokości
        font_size = max_font_size
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        logging.warning(f"Nie znaleziono czcionki {font_path}. Używanie domyślnej.")
        font = ImageFont.load_default()
        # Starsze wersje Pillow mogą wymagać innego podejścia do rozmiaru domyślnej czcionki
        try:
            # Próbujemy uzyskać rozmiar z domyślnej czcionki, jeśli to możliwe
            bbox = draw.textbbox((0, 0), "A", font=font)
            default_font_height = bbox[3] - bbox[1]
            font_size = default_font_height if default_font_height > 0 else 10
        except AttributeError:
            # Starsze wersje Pillow
            try:
                font_size = font.getsize("A")[1] if font.getsize("A")[1] > 0 else 10
            except AttributeError:
                font_size = 10  # Ostateczność

    # Funkcja pomocnicza do obliczania rozmiaru tekstu
    def get_text_dimensions(text, current_font):
        try:
            bbox = draw.textbbox((0, 0), text, font=current_font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            # Dla starszych wersji Pillow
            return draw.textsize(text, font=current_font)

    # Dzielimy nazwę gry na słowa
    words = game_name.split()
    lines = []
    current_line = ""
    line_height = 0

    # Dopasowanie rozmiaru czcionki i podział na linie
    while font_size > 8:  # Minimalny rozmiar czcionki
        lines = []
        current_line = ""
        possible = True
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()  # Użyj domyślnej, jeśli truetype zawiedzie

        line_width_check, line_height = get_text_dimensions(
            "A", font
        )  # Pobierz wysokość linii

        for word in words:
            test_line = f"{current_line} {word}".strip()
            w, h = get_text_dimensions(test_line, font)
            if w <= size[0] - 20:  # Zostaw margines 10px po bokach
                current_line = test_line
            else:
                if not current_line:  # Jeśli pojedyncze słowo jest za długie
                    possible = False
                    break  # Zmniejsz rozmiar czcionki
                lines.append(current_line)
                current_line = word
        if not possible:
            font_size -= 2
            continue  # Spróbuj z mniejszą czcionką

        lines.append(current_line)  # Dodaj ostatnią linię

        total_text_height = len(lines) * (
            line_height + 2
        )  # Dodaj mały odstęp między liniami
        if total_text_height <= size[1] - 20:  # Zostaw margines 10px góra/dół
            break  # Znaleziono odpowiedni rozmiar
        else:
            font_size -= 2  # Zmniejsz rozmiar czcionki

    # Rysowanie tekstu
    text_y = (
        size[1] - (len(lines) * (line_height + 2) - 2)
    ) // 2  # Wyśrodkowanie pionowe
    for line in lines:
        w, h = get_text_dimensions(line, font)
        text_x = (size[0] - w) // 2  # Wyśrodkowanie poziome
        draw.text((text_x, text_y), line, fill="white", font=font)
        text_y += line_height + 2  # Przejdź do następnej linii z odstępem

    try:
        image.save(image_path)
        logging.info(f"Zapisano domyślną okładkę: {image_path}")
        return image_path
    except Exception as e:
        logging.error(f"Nie można zapisać domyślnej okładki '{image_path}': {e}")
        return None  # Zwróć None w przypadku błędu zapisu


@functools.lru_cache(maxsize=512)  # Zwiększony cache dla PhotoImage
def load_photoimage_from_path(image_path, size):
    """
    Ładuje obraz z podanej ścieżki, skaluje go do podanego rozmiaru
    i tworzy obiekt PhotoImage, gotowy do użycia w Tkinter.
    Wynik jest cache'owany dla lepszej wydajności.
    Obsługuje błędy ładowania obrazu i zwraca domyślny obraz błędu.
    """
    if not image_path or not os.path.exists(image_path):
        logging.warning(
            f"Ścieżka obrazu nie istnieje lub jest pusta: '{image_path}'. Zwracam obraz błędu."
        )
        return create_error_photoimage(size)

    try:
        with Image.open(image_path) as img:
            # Konwersja do RGBA dla spójności i obsługi przezroczystości
            img = img.convert("RGBA")
            # Skalowanie z zachowaniem proporcji, jeśli to konieczne (choć miniatury powinny być ok)
            # img.thumbnail(size, RESAMPLING) # thumbnail zachowuje proporcje
            # Lub wymuszenie rozmiaru:
            img = img.resize(size, RESAMPLING)
            return ImageTk.PhotoImage(img)
    except (
        UnidentifiedImageError,
        FileNotFoundError,
        OSError,
        ValueError,
        SyntaxError,
    ) as e:
        # SyntaxError może wystąpić przy uszkodzonych plikach PNG
        logging.error(f"Błąd ładowania PhotoImage z '{image_path}': {e}")
        return create_error_photoimage(size)
    except Exception as e:  # Złap inne nieoczekiwane błędy
        logging.exception(
            f"Nieoczekiwany błąd podczas ładowania PhotoImage z '{image_path}': {e}"
        )
        return create_error_photoimage(size)


@functools.lru_cache(maxsize=1)  # Cache dla obrazka błędu (wystarczy 1)
def create_error_photoimage(size):
    """Tworzy i zwraca domyślny obiekt PhotoImage reprezentujący błąd ładowania."""
    try:
        error_img = Image.new("RGB", size, color="darkred")  # Ciemnoczerwone tło
        draw = ImageDraw.Draw(error_img)
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except IOError:
            font = ImageFont.load_default()
        draw.text(
            (10, 10), "Błąd\nładowania\nobrazu", fill="white", font=font, align="center"
        )
        return ImageTk.PhotoImage(error_img)
    except Exception as e:
        logging.error(f"Nie można utworzyć domyślnego obrazu błędu: {e}")
        # W ostateczności zwróć pusty PhotoImage, aby uniknąć crashu
        return ImageTk.PhotoImage(Image.new("RGB", size, color="black"))


def get_or_create_thumbnail(
    original_image_path, game_name, size=(DEFAULT_TILE_WIDTH, DEFAULT_TILE_HEIGHT)
):
    """
    Sprawdza, czy istnieje miniatura dla danego obrazu. Jeśli nie, tworzy ją.
    Zwraca ścieżkę do miniatury.
    Jeśli oryginalny obraz nie istnieje lub jest nieprawidłowy, próbuje utworzyć domyślną okładkę.
    """
    if not original_image_path or not os.path.exists(original_image_path):
        logging.warning(
            f"Oryginalny obraz dla '{game_name}' nie istnieje: '{original_image_path}'. Próba utworzenia domyślnej okładki."
        )
        # Zamiast tworzyć miniaturę z niczego, stwórz domyślną okładkę gry
        default_cover_path = create_default_cover(game_name, size)
        if default_cover_path:
            # Teraz spróbujmy utworzyć miniaturę z tej domyślnej okładki
            original_image_path = default_cover_path
        else:
            logging.error(
                f"Nie udało się utworzyć nawet domyślnej okładki dla '{game_name}'. Zwracam None."
            )
            return None  # Nie udało się uzyskać żadnego obrazu

    base_name = os.path.basename(original_image_path)
    name, ext = os.path.splitext(base_name)
    thumbnail_filename = f"{name}_thumb{ext}"
    thumbnail_path = os.path.join(THUMBNAIL_FOLDER, thumbnail_filename)

    # Sprawdź, czy miniatura istnieje i czy jest nowsza niż oryginał
    if os.path.exists(thumbnail_path) and os.path.getmtime(
        thumbnail_path
    ) >= os.path.getmtime(original_image_path):
        # Sprawdźmy jeszcze rozmiar miniatury - czy pasuje do oczekiwanego
        try:
            with Image.open(thumbnail_path) as thumb_img:
                if thumb_img.size == size:
                    # logging.debug(f"Używanie istniejącej miniatury: {thumbnail_path}")
                    return thumbnail_path
                else:
                    logging.info(
                        f"Rozmiar istniejącej miniatury {thumb_img.size} dla '{game_name}' różni się od oczekiwanego {size}. Tworzenie nowej."
                    )
        except (UnidentifiedImageError, OSError) as e:
            logging.warning(
                f"Istniejąca miniatura '{thumbnail_path}' jest uszkodzona: {e}. Tworzenie nowej."
            )

    logging.info(f"Tworzenie miniatury dla: {original_image_path} -> {thumbnail_path}")
    try:
        with Image.open(original_image_path) as img:
            img.thumbnail(size, RESAMPLING)  # Zachowuje proporcje, mieści w 'size'
            # Można dodać tło, jeśli chcemy mieć stały rozmiar miniatury
            # final_thumb = Image.new('RGBA', size, (0, 0, 0, 0)) # Przezroczyste tło
            # paste_x = (size[0] - img.width) // 2
            # paste_y = (size[1] - img.height) // 2
            # final_thumb.paste(img, (paste_x, paste_y))
            # final_thumb.save(thumbnail_path)

            # Lub po prostu zapisz przeskalowany obraz (może mieć inny rozmiar niż 'size', jeśli proporcje się różnią)
            img.convert("RGBA").save(thumbnail_path)  # Zapisz jako RGBA dla spójności

        return thumbnail_path
    except (UnidentifiedImageError, FileNotFoundError, OSError, ValueError) as e:
        logging.error(f"Nie można utworzyć miniatury dla '{original_image_path}': {e}")
        # Jeśli tworzenie miniatury zawiedzie, spróbuj zwrócić ścieżkę do domyślnej okładki
        default_cover = create_default_cover(game_name, size)
        if default_cover and os.path.exists(default_cover):
            # Spróbuj utworzyć miniaturę z domyślnej okładki
            return get_or_create_thumbnail(default_cover, game_name, size)
        return None  # Zwróć None, jeśli wszystko inne zawiedzie
    except Exception as e:
        logging.exception(
            f"Nieoczekiwany błąd podczas tworzenia miniatury dla '{original_image_path}': {e}"
        )
        return None
