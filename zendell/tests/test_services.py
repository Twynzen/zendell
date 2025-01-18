# /tests/test_services.py

import pytest
from services.llm_provider import ask_gpt

#@pytest.mark.skip(reason="Este test funciona correctamente y no requiere ser ejecutado ahora.")
@pytest.mark.parametrize("prompt", [
    "Hola, ¿cómo estás?",
    "¿Cuál es la capital de Francia?"
])
def test_ask_gpt_basic(prompt):
    """
    Test mejorado de la función ask_gpt con prompts sencillos.
    Imprime el prompt y la respuesta para depuración.
    """

    # Llamamos a la función ask_gpt con el prompt dado
    response = ask_gpt(prompt)

    # Imprimimos en consola el prompt y la respuesta recibida
    print(f"\n[TEST] Prompt: {prompt}")
    print(f"[TEST] Respuesta del modelo: {response}")

    # Verificamos que la respuesta no sea None
    assert response is not None, "La respuesta no debería ser None."

    # Verificamos que la respuesta tenga contenido
    assert len(response) > 0, "La respuesta debería contener texto."

    # Verificación extra: comprobar que la respuesta contiene alguna palabra clave esperada
    if "capital" in prompt.lower():
        assert "París" in response, "La respuesta debería mencionar 'París'."
