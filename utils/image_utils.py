"""
Narzędzia do przetwarzania obrazów
Zawiera funkcje pomocnicze do operacji na obrazach (PIL/Pillow).
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont, ImageTk, UnidentifiedImageError

logger = logging.getLogger(__name__)


def load_image(filepath: Union[str, Path]) -> Optional[Image.Image]:
    """
    Ładuje obraz z pliku.
    
    Args:
        filepath: Ścieżka do pliku obrazu
        
    Returns:
        Obiekt Image lub None w przypadku błędu
    """
    try:
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"Plik obrazu nie istnieje: {filepath}")
            return None
        
        image = Image.open(filepath)
        logger.debug(f"Załadowano obraz: {filepath}")
        return image
        
    except UnidentifiedImageError:
        logger.error(f"Nie można rozpoznać formatu obrazu: {filepath}")
        return None
        
    except Exception as e:
        logger.error(f"Błąd ładowania obrazu {filepath}: {e}")
        return None


def resize_image(image: Image.Image, 
                size: Tuple[int, int],
                keep_aspect: bool = True,
                resample: int = Image.LANCZOS) -> Image.Image:
    """
    Zmienia rozmiar obrazu.
    
    Args:
        image: Obraz do przeskalowania
        size: Docelowy rozmiar (width, height)
        keep_aspect: Czy zachować proporcje
        resample: Algorytm resamplingu
        
    Returns:
        Przeskalowany obraz
    """
    try:
        if keep_aspect:
            image.thumbnail(size, resample)
            return image
        else:
            return image.resize(size, resample)
            
    except Exception as e:
        logger.error(f"Błąd zmiany rozmiaru obrazu: {e}")
        return image


def create_thumbnail(filepath: Union[str, Path],
                    size: Tuple[int, int] = (200, 200),
                    output_path: Optional[Union[str, Path]] = None,
                    quality: int = 85) -> Optional[Path]:
    """
    Tworzy miniaturę obrazu.
    
    Args:
        filepath: Ścieżka do oryginalnego obrazu
        size: Rozmiar miniatury
        output_path: Ścieżka wyjściowa (None = auto)
        quality: Jakość JPEG (1-100)
        
    Returns:
        Ścieżka do utworzonej miniatury lub None
    """
    try:
        filepath = Path(filepath)
        image = load_image(filepath)
        
        if image is None:
            return None
        
        # Zmień rozmiar
        image.thumbnail(size, Image.LANCZOS)
        
        # Ustal ścieżkę wyjściową
        if output_path is None:
            output_path = filepath.parent / f"{filepath.stem}_thumb{filepath.suffix}"
        else:
            output_path = Path(output_path)
        
        # Zapisz
        image.save(output_path, quality=quality, optimize=True)
        logger.debug(f"Utworzono miniaturę: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Błąd tworzenia miniatury {filepath}: {e}")
        return None


def save_image(image: Image.Image,
              filepath: Union[str, Path],
              quality: int = 95,
              optimize: bool = True) -> bool:
    """
    Zapisuje obraz do pliku.
    
    Args:
        image: Obraz do zapisania
        filepath: Ścieżka docelowa
        quality: Jakość dla JPEG (1-100)
        optimize: Czy optymalizować plik
        
    Returns:
        True jeśli zapisano pomyślnie
    """
    try:
        filepath = Path(filepath)
        
        # Utwórz katalog jeśli nie istnieje
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Zapisz z odpowiednimi parametrami
        save_kwargs = {'optimize': optimize}
        
        if filepath.suffix.lower() in ['.jpg', '.jpeg']:
            save_kwargs['quality'] = quality
        
        image.save(filepath, **save_kwargs)
        logger.debug(f"Zapisano obraz: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd zapisywania obrazu {filepath}: {e}")
        return False


def get_image_size(filepath: Union[str, Path]) -> Optional[Tuple[int, int]]:
    """
    Zwraca rozmiar obrazu bez pełnego ładowania.
    
    Args:
        filepath: Ścieżka do obrazu
        
    Returns:
        Tuple (width, height) lub None
    """
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception as e:
        logger.error(f"Błąd pobierania rozmiaru obrazu {filepath}: {e}")
        return None


def image_to_base64(image: Image.Image, format: str = 'PNG') -> Optional[str]:
    """
    Konwertuje obraz PIL do base64.
    
    Args:
        image: Obraz PIL
        format: Format obrazu (PNG, JPEG, etc.)
        
    Returns:
        String base64 lub None
    """
    try:
        buffer = BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return img_base64
        
    except Exception as e:
        logger.error(f"Błąd konwersji obrazu do base64: {e}")
        return None


def base64_to_image(base64_string: str) -> Optional[Image.Image]:
    """
    Konwertuje base64 do obrazu PIL.
    
    Args:
        base64_string: String base64
        
    Returns:
        Obraz PIL lub None
    """
    try:
        img_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(img_data))
        return image
        
    except Exception as e:
        logger.error(f"Błąd konwersji base64 do obrazu: {e}")
        return None


def create_gradient(size: Tuple[int, int],
                   color1: Tuple[int, int, int],
                   color2: Tuple[int, int, int],
                   direction: str = 'vertical') -> Image.Image:
    """
    Tworzy obraz z gradientem.
    
    Args:
        size: Rozmiar obrazu (width, height)
        color1: Kolor początkowy RGB
        color2: Kolor końcowy RGB
        direction: Kierunek ('vertical' lub 'horizontal')
        
    Returns:
        Obraz z gradientem
    """
    try:
        base = Image.new('RGB', size, color1)
        top = Image.new('RGB', size, color2)
        
        mask = Image.new('L', size)
        mask_data = []
        
        if direction == 'vertical':
            for y in range(size[1]):
                mask_data.extend([int(255 * (y / size[1]))] * size[0])
        else:  # horizontal
            for y in range(size[1]):
                for x in range(size[0]):
                    mask_data.append(int(255 * (x / size[0])))
        
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        
        return base
        
    except Exception as e:
        logger.error(f"Błąd tworzenia gradientu: {e}")
        return Image.new('RGB', size, color1)


def add_text_to_image(image: Image.Image,
                     text: str,
                     position: Tuple[int, int],
                     font_size: int = 20,
                     color: Tuple[int, int, int] = (255, 255, 255),
                     font_path: Optional[str] = None) -> Image.Image:
    """
    Dodaje tekst do obrazu.
    
    Args:
        image: Obraz bazowy
        text: Tekst do dodania
        position: Pozycja tekstu (x, y)
        font_size: Rozmiar czcionki
        color: Kolor tekstu RGB
        font_path: Ścieżka do czcionki TTF (None = domyślna)
        
    Returns:
        Obraz z tekstem
    """
    try:
        # Utwórz kopię obrazu
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Załaduj czcionkę
        if font_path and Path(font_path).exists():
            font = ImageFont.truetype(font_path, font_size)
        else:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # Narysuj tekst
        draw.text(position, text, font=font, fill=color)
        
        return img_copy
        
    except Exception as e:
        logger.error(f"Błąd dodawania tekstu do obrazu: {e}")
        return image


def crop_to_aspect_ratio(image: Image.Image,
                         aspect_ratio: Tuple[int, int]) -> Image.Image:
    """
    Przycina obraz do określonych proporcji.
    
    Args:
        image: Obraz do przycięcia
        aspect_ratio: Proporcje (width, height), np. (16, 9)
        
    Returns:
        Przycięty obraz
    """
    try:
        target_ratio = aspect_ratio[0] / aspect_ratio[1]
        current_ratio = image.width / image.height
        
        if abs(current_ratio - target_ratio) < 0.01:
            return image  # Już ma odpowiednie proporcje
        
        if current_ratio > target_ratio:
            # Obraz jest za szeroki, przytnij boki
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            box = (left, 0, left + new_width, image.height)
        else:
            # Obraz jest za wysoki, przytnij góra/dół
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            box = (0, top, image.width, top + new_height)
        
        return image.crop(box)
        
    except Exception as e:
        logger.error(f"Błąd przycinania obrazu: {e}")
        return image


def apply_blur(image: Image.Image, radius: int = 5) -> Image.Image:
    """
    Aplikuje rozmycie do obrazu.
    
    Args:
        image: Obraz do rozmycia
        radius: Promień rozmycia
        
    Returns:
        Rozmyty obraz
    """
    try:
        from PIL import ImageFilter
        return image.filter(ImageFilter.GaussianBlur(radius))
    except Exception as e:
        logger.error(f"Błąd rozmywania obrazu: {e}")
        return image


def create_placeholder_image(size: Tuple[int, int],
                            text: str = "No Image",
                            bg_color: Tuple[int, int, int] = (50, 50, 50),
                            text_color: Tuple[int, int, int] = (150, 150, 150)) -> Image.Image:
    """
    Tworzy obraz zastępczy z tekstem.
    
    Args:
        size: Rozmiar obrazu
        text: Tekst do wyświetlenia
        bg_color: Kolor tła RGB
        text_color: Kolor tekstu RGB
        
    Returns:
        Obraz zastępczy
    """
    try:
        image = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(image)
        
        # Oblicz pozycję tekstu (wyśrodkuj)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Pobierz rozmiar tekstu
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
        
        draw.text(position, text, font=font, fill=text_color)
        
        return image
        
    except Exception as e:
        logger.error(f"Błąd tworzenia obrazu zastępczego: {e}")
        return Image.new('RGB', size, bg_color)
