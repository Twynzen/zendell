# ZENDELL
 Un ecosistema de múltiples agentes inteligentes que se coordinan para asistir a un usuario a lo largo de su día, recopilando y organizando información, analizando sus necesidades, brindando recordatorios, sugerencias y guía continua. Cada agente se especializa en una tarea (recolección de datos, análisis, recomendaciones, comunicación, etc.) y comparten un estado global que evoluciona con las interacciones del usuario. El objetivo es convertirse en un asistente “super inteligente” que no solo genere texto, sino que cumpla activamente los objetivos del usuario, automatizando procesos y anticipando soluciones en base a la información recibida cada hora y las metas planteadas. La idea es que el sistema sea capaz de acompañar, recordar, y ayudar de forma fluida, armoniosa y casi humana.

 https://www.mermaidchart.com/app/projects/d9ff5e08-4fdf-412e-8f1a-55d8e15bc833/diagrams/e3f8fb68-0d1e-4097-bc9c-4302d118bfe8/version/v0.1/edit

                                      
┌───────────────────────────────────────────────┐
│ 1. Configuración del Sistema (System Config) │
│    - "zendell" se define y se guarda en DB   │
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 2. Usuario Nuevo / get_state()              │
│    - Se busca user_id en BD                 │
│    - Si no existe, se crea con campos vacíos│
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 3. (Primer Mensaje)                          │
│    - Se genera un saludo inicial (LLM)       │
│    - Se manda por Discord                    │
│    - Se guarda en conversation_logs          │
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 4. Usuario Responde                          │
│    - on_user_message() se dispara            │
│    - Se guarda el texto en conversation_logs │
│      (array messages)                        │
│    - Se actualiza user_state (last_interact) │
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 5. Análisis de Datos                         │
│    - Multi-Agente (activity_collector,       │
│      analyzer, etc.)                         │
│    - Etiquetar: tono, intención, metas...    │
│    - Se guardan resultados en BD (Ej.        │
│      conversation_logs o user_state)         │
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 6. Recomendaciones                           │
│    - Se pregunta a LLM (recommender)         │
│    - Se generan sugerencias/acciones         │
│    - Se guardan en DB                        │
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 7. Respuesta al Usuario                      │
│    - Se unifica análisis + recomendación     │
│    - Se envía mensaje final por Discord      │
│    - Se agrega en conversation_logs (role=ai)│
└───────────────────────────────────────────────┘
                |
                ▼
┌───────────────────────────────────────────────┐
│ 8. Ciclo Cada Hora                           │
│    - Comprobar si last_interaction_time ≥ 1h │
│    - Disparar el flujo (3) => (7) otra vez    │
└───────────────────────────────────────────────┘
