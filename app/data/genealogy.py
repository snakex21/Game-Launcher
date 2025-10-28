"""
W tym pliku znajdują się wszystkie dane i funkcje do obsługi statystyk genealogicznych.
"""
from datetime import datetime, timedelta
from collections import Counter
import random

def get_genealogy_data():
    """Zwraca przykładowe dane genealogiczne."""
    # Prosty mock danych, który będziemy mogli zastąpić w przyszłości
    return [
        {"birth_date": "1820-05-15", "death_date": "1890-03-20", "household_number": "h1", "children": 5},
        {"birth_date": "1822-11-01", "death_date": "1823-01-15", "household_number": "h1", "children": 0}, # Śmiertelność niemowląt
        {"birth_date": "1845-02-10", "death_date": "1910-10-05", "household_number": "h2", "children": 8},
        {"birth_date": "1850-07-22", "death_date": "1850-08-10", "household_number": "h2", "children": 0}, # Śmiertelność niemowląt
        {"birth_date": "1870-01-30", "death_date": "1950-12-12", "household_number": "h3", "children": 3},
    ]

def calculate_infant_mortality(data):
    """Oblicza statystyki śmiertelności niemowląt."""
    infants = [p for p in data if p["death_date"] and (datetime.strptime(p["death_date"], "%Y-%m-%d") - datetime.strptime(p["birth_date"], "%Y-%m-%d")).days <= 365]
    total_births = len(data)
    
    if not infants:
        return {"labels": [], "values": [], "percentage": 0}

    mortality_distribution = {
        "0-7 dni": 0,
        "8-30 dni": 0,
        "1-6 miesięcy": 0,
        "6-12 miesięcy": 0,
    }

    for infant in infants:
        life_days = (datetime.strptime(infant["death_date"], "%Y-%m-%d") - datetime.strptime(infant["birth_date"], "%Y-%m-%d")).days
        if 0 <= life_days <= 7:
            mortality_distribution["0-7 dni"] += 1
        elif 8 <= life_days <= 30:
            mortality_distribution["8-30 dni"] += 1
        elif 31 <= life_days <= 180:
            mortality_distribution["1-6 miesięcy"] += 1
        else:
            mortality_distribution["6-12 miesięcy"] += 1
            
    return {
        "labels": list(mortality_distribution.keys()),
        "values": list(mortality_distribution.values()),
        "percentage": (len(infants) / total_births) * 100 if total_births > 0 else 0,
    }

def calculate_life_expectancy(data):
    """Oblicza średnią długość życia w dekadach."""
    decades = {}
    for person in data:
        if person["death_date"]:
            birth_year = datetime.strptime(person["birth_date"], "%Y-%m-%d").year
            death_year = datetime.strptime(person["death_date"], "%Y-%m-%d").year
            age = death_year - birth_year
            decade = (birth_year // 10) * 10
            if decade not in decades:
                decades[decade] = []
            decades[decade].append(age)
    
    avg_life_expectancy = {d: sum(ages) / len(ages) for d, ages in decades.items()}
    sorted_decades = sorted(avg_life_expectancy.keys())
    
    return {
        "labels": [f"{d}-{d+9}" for d in sorted_decades],
        "values": [avg_life_expectancy[d] for d in sorted_decades],
    }

def calculate_seasonality(data):
    """Oblicza sezonowość urodzeń i zgonów."""
    birth_months = Counter(datetime.strptime(p["birth_date"], "%Y-%m-%d").month for p in data)
    death_months = Counter(datetime.strptime(p["death_date"], "%Y-%m-%d").month for p in data if p["death_date"])
    
    months = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]
    
    return {
        "labels": months,
        "births": [birth_months[i] for i in range(1, 13)],
        "deaths": [death_months[i] for i in range(1, 13)],
    }

def calculate_family_structure(data):
    """Oblicza statystyki struktury rodzin."""
    family_sizes = Counter(p["children"] for p in data if p.get("children", 0) > 0)
    
    # Grupowanie wielkości rodzin
    size_distribution = {
        "1 dziecko": 0,
        "2 dzieci": 0,
        "3-5 dzieci": 0,
        "6-10 dzieci": 0,
        ">10 dzieci": 0,
    }
    for size, count in family_sizes.items():
        if size == 1:
            size_distribution["1 dziecko"] += count
        elif size == 2:
            size_distribution["2 dzieci"] += count
        elif 3 <= size <= 5:
            size_distribution["3-5 dzieci"] += count
        elif 6 <= size <= 10:
            size_distribution["6-10 dzieci"] += count
        else:
            size_distribution[">10 dzieci"] += count
            
    total_families = sum(1 for p in data if p.get("children", 0) > 0)
    total_children = sum(p["children"] for p in data)
    
    return {
        "labels": list(size_distribution.keys()),
        "values": list(size_distribution.values()),
        "avg_children": total_children / total_families if total_families > 0 else 0,
    }
