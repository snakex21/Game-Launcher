import datetime
import logging
import re


def _check_game_against_rules(self, game_data, rules):
    """Sprawdza, czy dane gry spełniają podaną listę reguł filtra (logika AND)."""
    if not rules:
        return True

    ops = {
        "text": {
            "zawiera": lambda val, field: str(val).lower() in str(field).lower(),
            "nie zawiera": lambda val, field: str(val).lower() not in str(field).lower(),
            "równa się": lambda val, field: str(field).lower() == str(val).lower(),
            "zaczyna się od": lambda val, field: str(field).lower().startswith(str(val).lower()),
            "kończy się na": lambda val, field: str(field).lower().endswith(str(val).lower()),
            "jest ustawione": lambda val, field: bool(field),
            "nie jest ustawione": lambda val, field: not field,
        },
        "list": {
            "zawiera": lambda val, field: (str(val) in field if isinstance(field, list) else False),
            "nie zawiera": lambda val, field: (
                str(val) not in field if isinstance(field, list) else True
            ),
            "jest ustawione": lambda val, field: bool(field),
            "nie jest ustawione": lambda val, field: not field,
        },
        "number": {
            "==": lambda val, field: (float(field) == float(val) if field is not None else False),
            "!=": lambda val, field: (float(field) != float(val) if field is not None else True),
            ">": lambda val, field: (float(field) > float(val) if field is not None else False),
            "<": lambda val, field: (float(field) < float(val) if field is not None else False),
            ">=": lambda val, field: (float(field) >= float(val) if field is not None else False),
            "<=": lambda val, field: (float(field) <= float(val) if field is not None else False),
            "jest ustawione": lambda val, field: field is not None,
            "nie jest ustawione": lambda val, field: field is None,
        },
        "date": {
            "jest równe": lambda val, field: (str(field) == str(val) if field else False),
            "jest przed": lambda val, field: (str(field) < str(val) if field and val else False),
            "jest po": lambda val, field: (str(field) > str(val) if field and val else False),
            "jest ustawione": lambda val, field: bool(field),
            "nie jest ustawione": lambda val, field: not field,
        },
        "choice": {
            "jest": lambda val, field: str(field) == str(val),
            "nie jest": lambda val, field: str(field) != str(val),
            "jest ustawione": lambda val, field: bool(field),
            "nie jest ustawione": lambda val, field: not field,
        },
    }

    for rule in rules:
        field_key = rule.get("field")
        operator_key = rule.get("operator")
        rule_value = rule.get("value")

        if not field_key or not operator_key:
            logging.warning(f"Pominięto niekompletną regułę: {rule}")
            continue

        field_value = game_data.get(field_key)
        field_type = None
        for _, data in self.FIELDS.items():
            if data["db_field"] == field_key:
                field_type = data["type"]
                break

        if field_type is None:
            if isinstance(field_value, list):
                field_type = "list"
            elif isinstance(field_value, (int, float)):
                field_type = "number"
            elif isinstance(field_value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", field_value):
                field_type = "date"
            else:
                field_type = "text"
            logging.debug(
                f"Nie znaleziono typu dla pola '{field_key}', zgadnięto: {field_type}"
            )

        if field_key == "play_time":
            field_value = round(game_data.get("play_time", 0) / 3600, 2)
            field_type = "number"
        elif field_key in ["date_added", "last_played"]:
            timestamp = game_data.get(field_key)
            field_value = (
                datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                if timestamp
                else None
            )
            field_type = "date"
        elif field_key == "game_type":
            field_value = game_data.get("game_type", "pc")
            field_type = "choice"
        elif field_key == "emulator_name":
            field_value = game_data.get("emulator_name")
            field_type = "choice"

        operator_set = ops.get(field_type)
        if not operator_set:
            logging.warning(
                f"Brak zdefiniowanych operatorów dla typu pola '{field_type}' (pole: {field_key})"
            )
            return False

        if field_type == "list":
            if operator_key == "zawiera":
                op_func = operator_set.get("zawiera (lista)")
            elif operator_key == "nie zawiera":
                op_func = operator_set.get("nie zawiera (lista)")
            else:
                op_func = operator_set.get(operator_key)
        else:
            op_func = operator_set.get(operator_key)

        if not op_func:
            logging.warning(
                f"Nieznany lub nieobsługiwany operator '{operator_key}' dla typu '{field_type}' w regule: {rule}"
            )
            return False

        try:
            rule_met = False
            if operator_key in ["jest ustawione", "nie jest ustawione"]:
                rule_met = op_func(None, field_value)
            elif field_value is not None or field_type == "text":
                compare_value = rule_value
                if field_type == "number":
                    try:
                        compare_value = float(rule_value)
                    except (ValueError, TypeError) as conv_err:
                        raise ValueError(
                            f"Wartość reguły '{rule_value}' nie jest poprawną liczbą: {conv_err}"
                        )

                rule_met = op_func(compare_value, field_value)
            else:
                rule_met = False

            if not rule_met:
                logging.debug(
                    f"Gra '{game_data.get('name')}' nie spełnia reguły: {rule} (wartość pola: {field_value})"
                )
                return False
        except ValueError as ve:
            logging.error(
                f"Błąd wartości w regule {rule} dla gry {game_data.get('name')}: {ve}"
            )
            return False
        except Exception as e:
            logging.exception(
                f"Błąd podczas stosowania reguły {rule} do gry {game_data.get('name')}: {e}"
            )
            return False

    logging.debug(f"Gra '{game_data.get('name')}' spełnia wszystkie reguły filtra.")
    return True


__all__ = ["_check_game_against_rules"]
