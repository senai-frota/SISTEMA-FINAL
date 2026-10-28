def para_maiusculas(valor):
    """Normaliza texto livre para uppercase; preserva None/vazio."""
    if valor is None:
        return valor
    if not isinstance(valor, str):
        return valor
    texto = valor.strip()
    if not texto:
        return texto
    return texto.upper()


def aplicar_maiusculas(validated_data, campos):
    """Aplica uppercase nos campos informados presentes em validated_data."""
    for campo in campos:
        if campo in validated_data and validated_data[campo] is not None:
            validated_data[campo] = para_maiusculas(validated_data[campo])
    return validated_data
