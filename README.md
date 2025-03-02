CONTEXTO DEL PROYECTO ACTUAL: # ZENDELL: Ecosistema Multiagente Proactivo

> **Asistente “super inteligente” que te acompaña durante el día, iniciando conversaciones, recopilando información y adaptándose a tus necesidades.**  

## 1. ZENDELL es un conjunto de agentes inteligentes que trabajan en equipo para:

1. **Conocer actividades hora a hora del usuario.
2. **Analizar información del usuario para comprenderlo y entenderlo tanto fisica como mentalmente.
3. **Interactuar proactivamente** cada hora (o en intervalos configurables).
4. **Evolucionar, guardando un perfil en una base de datos (MongoDB) y utilizando por el momento (Discord, WhatsApp, correo, ) para comunicarse con el usuario.

El objetivo final es que ZENDELL sea como un “mejor amigo/ maestro y guia”, siempre al tanto de lo que necesita (sacando información, analizándola y eventualemnte al tener una amplia cantidad de datos aportar al usuario con sus necesidades, recordatorios, consejos, apoyo y prioridade).

## 2. Características Clave

- **Conversaciones Proactivas**: No espera a que el usuario hable; cada hora (o cuando se configures) inicia un diálogo/conversación.
- **Agentes Especializados**: Cada módulo (collector, analyzer, recommender, communicator, etc.) se encarga de una tarea concreta, (Esto debe ser ampliable con el fin de que si a futuro salen nuevas tecnologias o agentes de IA pueda embeberlos como un agente más al sistema, ejemplo: Un agente que busca noticias relevantes en internet y le avisa de una inversión especifica sobre x acción de empresa).
- **Memoria y Aprendizaje**: Gracias a la base de datos y la orquestación, ZENDELL va recordando las conversaciones, aprendiendo sobre el usuario y razonando sobre sus necesidades.
- **Integración con LLMs**: Para generar textos, extraer información del usuario y crear recomendaciones personalizadas.
- **Escalabilidad**: Arquitectura modular que permite añadir fácilmente nuevos agentes o servicios de mensajería.

## 3. Arquitectura del Proyecto

El proyecto se organiza en varias carpetas clave dentro de `zendell/`:

### **1. agents/**  
- `activity_collector.py`: Recopila actividades del usuario y las almacena en su perfil.  
- `analyzer.py`: Analiza la información recogida para determinar estado de ánimo y patrones de comportamiento.  
- `communicator.py`: Actúa como el “centro de mensajes”: recibe textos del usuario, los delega y guarda la conversación.  
- `goal_finder.py`: Decide cuándo iniciar interacciones y prepara los mensajes iniciales o de seguimiento.  
- `orchestrator.py`: Coordina el flujo completo, combinando los resultados de los demás agentes.  
- `recommender.py`: Basándose en los análisis, da consejos y acciones prácticas.

### **2. config/**  
- `settings.py`: Guarda tokens, API keys, configuraciones varias (p. ej. `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`).  

### **3. core/**  
- `api.py`: (Opcional) Interfaz para exponer servicios vía API.  
- `db.py`: Maneja la conexión a MongoDB (operaciones con usuarios, estados, actividades, logs).  
- `graph.py`: Define el flujo de interacción en un grafo de estados.  
- `utils.py`: Funciones de ayuda para validaciones, manejo de tiempos, etc.

### **4. services/**  
- `discord_service.py`: Implementa un bot de Discord que recibe y envía mensajes al usuario.  
- `llm_provider.py`: Interfaz para llamar a OpenAI GPT.  
- `messaging_service.py`: Pensado para integrar otros canales (WhatsApp, email, etc.).  


Adicionalmente, hay archivos de configuración (`docker-compose.yml`, `pyproject.toml`, `requirements.txt`, etc.) para desplegar o instalar dependencias.

## 4. Flujo de Ejecución

### **1. Arranque (main.py)**  
- Conecta con MongoDB a través de `MongoDBManager`.  
- Inicia el bot de Discord (o cualquier otro canal).  

### **2. Bot de Discord**  
- Cuando se conecta, envía un saludo inicial al canal configurado.  
- Al recibir mensajes del usuario (`on_message`), los pasa a `communicator.py` para almacenarlos y procesarlos.  

### **3. Interacción Proactiva**  
- Cada hora (configurable), se revisa la lista de usuarios activos y se dispara `communicator.trigger_interaction(user_id)`.  
- Esto inicia el flujo del **Goal Finder**, que decide qué mensaje enviar o qué datos extraer.  

### **4. Orquestación**  
- **Orchestrator** llama a:  
  1. **Activity Collector** → almacena nueva info.  
  2. **Analyzer** → analiza estado de ánimo y patrones.  



### **5. Persistencia**  
- Todo se guarda en MongoDB: desde datos de usuario hasta logs de conversación, permitiendo rastrear el historial y mejorar la experiencia.  

## 5. Funcionamiento en la Práctica

Ejemplos de primera conversación con el usuario: 

Ejemplo 1: Consultoría de Marketing Digital
Zendell APP — 17:00
¡Hola! Soy Zendell, un sistema multiagente diseñado para asistirte en todo lo que necesites. ¿Cómo te llamas y a qué te dedicas?
(ETAPA: Inicial. Razonamiento: Obtener datos básicos del usuario para complementar el perfil.)

Usuario (Mariana) — 17:01
Me llamo Mariana y soy especialista en marketing digital.
(ETAPA: Registro de perfil. Razonamiento: Se confirma la ocupación para futuras recomendaciones.)

Zendell APP — 17:01
¿Qué hiciste entre las 16:00 y las 17:00, Mariana?
(ETAPA: ask_last_hour. Razonamiento: Recopilar actividad reciente para análisis de productividad.)

Mariana — 17:02
Estuve revisando campañas de publicidad y analizando métricas de conversión.
(ETAPA: Clarifier_last_hour. Razonamiento: El usuario ofrece actividad general; se deberá profundizar para detalles.)

Zendell APP — 17:02
¿Qué métricas específicas revisaste y qué ajustes consideras necesarios?
(ETAPA: Clarifier_last_hour. Razonamiento: Profundizar en los detalles para un mejor análisis.)

Mariana — 17:03
Me enfoqué en el CTR y la tasa de conversión, y creo que hay margen para mejorar el presupuesto de ciertos anuncios.
(ETAPA: Clarifier_last_hour. Razonamiento: Registro detallado de la actividad pasada.)

Zendell APP — 17:03
¿Qué planeas hacer entre las 17:03 y las 18:03, Mariana?
(ETAPA: ask_next_hour. Razonamiento: Consultar la actividad futura para complementar el análisis y planificar próximos pasos.)

Mariana — 17:04
Voy a ajustar el presupuesto y crear un informe detallado sobre el desempeño de las campañas.
(ETAPA: Clarifier_next_hour. Razonamiento: Se requiere profundizar sobre la estrategia a seguir.)

Zendell APP — 17:04
¿Qué aspectos específicos del informe o ajustes en el presupuesto implementarás?
(ETAPA: Clarifier_next_hour. Razonamiento: Recabar información precisa para generar recomendaciones.)

Mariana — 17:05
Analizaré el retorno de inversión de cada anuncio y ajustaré los presupuestos según el desempeño.
(ETAPA: Clarifier_next_hour. Razonamiento: Confirmación de la actividad futura y recopilación completa de datos.)

Zendell APP — 17:05
Gracias, Mariana. Toda la información ha sido registrada. Estoy aquí para apoyarte en lo que necesites. ¡Hasta pronto!
(ETAPA: Final. Razonamiento: Cierre del flujo, confirmando la recolección de datos.)

Ejemplo 2: Sesión de Entrenamiento Personal
Zendell APP — 07:30
¡Hola! Soy Zendell, un sistema multiagente listo para asistirte. ¿Cuál es tu nombre y a qué te dedicas?
(ETAPA: Inicial. Razonamiento: Establecer identidad y ocupación del usuario.)

Usuario (Carlos) — 07:31
Soy Carlos, entrenador personal y aficionado al fitness.
(ETAPA: Registro de perfil. Razonamiento: Registro de la ocupación para personalizar la experiencia.)

Zendell APP — 07:31
¿Qué hiciste entre las 06:30 y las 07:30, Carlos?
(ETAPA: ask_last_hour. Razonamiento: Recoger datos de actividad reciente para analizar el rendimiento.)

Carlos — 07:32
Realicé una sesión de cardio y algo de entrenamiento de fuerza.
(ETAPA: Clarifier_last_hour. Razonamiento: La respuesta es general; se requiere profundizar.)

Zendell APP — 07:32
¿Qué ejercicios específicos de fuerza realizaste y cómo te sentiste durante el cardio?
(ETAPA: Clarifier_last_hour. Razonamiento: Recoger detalles para evaluar la intensidad y efectividad.)

Carlos — 07:33
Hice sentadillas, press de banca y sentí que el cardio fue intenso, especialmente en las cuestas.
(ETAPA: Clarifier_last_hour. Razonamiento: Registro detallado de la actividad pasada.)

Zendell APP — 07:33
¿Qué planeas hacer entre las 07:33 y las 08:33, Carlos?
(ETAPA: ask_next_hour. Razonamiento: Consultar sobre el plan a corto plazo para ajustar rutinas o dar recomendaciones.)

Carlos — 07:34
Voy a enfocar mi entrenamiento en estiramientos y una sesión de yoga para recuperar energías.
(ETAPA: Clarifier_next_hour. Razonamiento: Se profundiza en la actividad futura para un plan de recuperación.)

Zendell APP — 07:34
¿Qué rutinas de estiramiento o técnicas de yoga planeas incorporar?
(ETAPA: Clarifier_next_hour. Razonamiento: Detallar para optimizar recomendaciones y seguimiento.)

Carlos — 07:35
Planeo hacer estiramientos de piernas y espalda, y probar una secuencia de yoga centrada en la respiración.
(ETAPA: Clarifier_next_hour. Razonamiento: Confirmación de la acción futura, completando el registro.)

Zendell APP — 07:35
Gracias, Carlos. Toda la información ha sido registrada. ¡Estoy aquí para ayudarte en cada paso!
(ETAPA: Final. Razonamiento: Cierre del flujo y confirmación de la recolección de datos.)

Ejemplo 3: Progreso en un Proyecto de Diseño Gráfico
Zendell APP — 14:00
¡Hola! Soy Zendell, tu asistente multiagente. ¿Cómo te llamas y a qué te dedicas?
(ETAPA: Inicial. Razonamiento: Identificar al usuario para personalizar el diálogo.)

Usuario (Lucía) — 14:01
Soy Lucía, diseñadora gráfica freelance, enfocada en branding y packaging.
(ETAPA: Registro de perfil. Razonamiento: Recopilar datos para adaptar sugerencias y análisis.)

Zendell APP — 14:01
¿Qué hiciste entre las 13:00 y las 14:00, Lucía?
(ETAPA: ask_last_hour. Razonamiento: Recoger actividad reciente para evaluar el progreso creativo.)

Lucía — 14:02
Estuve creando conceptos para una nueva línea de empaques sostenibles.
(ETAPA: Clarifier_last_hour. Razonamiento: La respuesta es general; se pide más detalle para análisis.)

Zendell APP — 14:02
¿Qué conceptos o ideas exploraste y qué herramientas utilizaste?
(ETAPA: Clarifier_last_hour. Razonamiento: Profundizar en detalles para entender el proceso creativo.)

Lucía — 14:03
Probé varios esquemas de color y utilicé Illustrator y Photoshop para esbozar ideas.
(ETAPA: Clarifier_last_hour. Razonamiento: Registro detallado que permite evaluar la metodología.)

Zendell APP — 14:03
¿Qué planeas hacer entre las 14:03 y las 15:03, Lucía?
(ETAPA: ask_next_hour. Razonamiento: Consultar la acción futura para dar seguimiento al flujo de trabajo.)

Lucía — 14:04
Voy a elegir el mejor concepto y desarrollar prototipos más detallados.
(ETAPA: Clarifier_next_hour. Razonamiento: Se requiere especificar para prever necesidades de apoyo o herramientas.)

Zendell APP — 14:04
¿Cómo piensas desarrollar esos prototipos y qué elementos clave incorporarás?
(ETAPA: Clarifier_next_hour. Razonamiento: Profundizar en los detalles futuros para análisis y seguimiento.)

Lucía — 14:05
Integraré texturas y tipografías que refuercen el mensaje ecológico, y usaré mockups para presentarlos.
(ETAPA: Clarifier_next_hour. Razonamiento: Completar el registro de la actividad futura.)

Zendell APP — 14:05
Gracias, Lucía. Toda la información ha sido registrada. ¡Quedo a tu disposición para lo que necesites!
(ETAPA: Final. Razonamiento: Cierre del flujo con confirmación de recolección de datos.)

Ejemplo 4: Sesión de Estudio en Ingeniería de Software
Zendell APP — 20:00
¡Hola! Soy Zendell, un sistema multiagente preparado para asistirte. ¿Cuál es tu nombre y en qué trabajas?
(ETAPA: Inicial. Razonamiento: Obtener datos iniciales para adaptar el seguimiento.)

Usuario (Andrés) — 20:01
Soy Andrés, ingeniero de software enfocado en desarrollo web.
(ETAPA: Registro de perfil. Razonamiento: Confirmar la especialidad para contextualizar futuras preguntas.)

Zendell APP — 20:01
¿Qué hiciste entre las 19:00 y las 20:00, Andrés?
(ETAPA: ask_last_hour. Razonamiento: Recopilar actividad reciente para análisis de progreso.)

Andrés — 20:02
Estuve revisando documentación y resolviendo dudas sobre microservicios.
(ETAPA: Clarifier_last_hour. Razonamiento: Respuesta general que requiere detalle para análisis.)

Zendell APP — 20:02
¿Qué temas específicos de microservicios abordaste y qué dudas resolviste?
(ETAPA: Clarifier_last_hour. Razonamiento: Profundizar para entender el contenido estudiado.)

Andrés — 20:03
Profundicé en la arquitectura de contenedores y cómo implementar escalabilidad en entornos distribuidos.
(ETAPA: Clarifier_last_hour. Razonamiento: Registro detallado de la actividad pasada.)

Zendell APP — 20:03
¿Qué planeas hacer entre las 20:03 y las 21:03, Andrés?
(ETAPA: ask_next_hour. Razonamiento: Consultar el plan inmediato para alinear el seguimiento y análisis.)

Andrés — 20:04
Voy a practicar implementando un servicio en Docker y realizar pruebas de integración.
(ETAPA: Clarifier_next_hour. Razonamiento: Se pide detalle sobre la acción futura para evaluar la metodología.)

Zendell APP — 20:04
¿Qué pasos específicos seguirás en la implementación y qué aspectos probarás en la integración?
(ETAPA: Clarifier_next_hour. Razonamiento: Profundizar en la planificación para optimizar el soporte.)

Andrés — 20:05
Configuraré el entorno de Docker, escribiré scripts de despliegue y probaré la comunicación entre servicios usando API REST.
(ETAPA: Clarifier_next_hour. Razonamiento: Completa la información necesaria para el análisis futuro.)

Zendell APP — 20:05
Gracias, Andrés. Toda la información ha sido registrada. ¡Estoy aquí para apoyarte en cada paso!
(ETAPA: Final. Razonamiento: Cierre del flujo, confirmación de recolección de datos.)

Ejemplo 5: Planificación de un Proyecto de Investigación
Zendell APP — 11:00
¡Hola! Soy Zendell, tu asistente multiagente. ¿Cuál es tu nombre y a qué te dedicas?
(ETAPA: Inicial. Razonamiento: Obtener información básica del usuario para personalizar el flujo.)

Usuario (Elena) — 11:01
Soy Elena, investigadora en biotecnología y me apasiona la ciencia aplicada.
(ETAPA: Registro de perfil. Razonamiento: Se establece la base para futuras recomendaciones y seguimiento.)

Zendell APP — 11:01
¿Qué hiciste entre las 10:00 y las 11:00, Elena?
(ETAPA: ask_last_hour. Razonamiento: Recopilar actividad reciente para evaluar el progreso en la investigación.)

Elena — 11:02
Estuve analizando resultados preliminares de mi experimento con cultivos celulares.
(ETAPA: Clarifier_last_hour. Razonamiento: La respuesta general necesita detalles para profundizar.)

Zendell APP — 11:02
¿Qué variables o resultados específicos examinaste en el experimento?
(ETAPA: Clarifier_last_hour. Razonamiento: Profundizar en los detalles para un análisis más completo.)

Elena — 11:03
Revisé la tasa de crecimiento y la viabilidad celular, y ajusté algunas concentraciones de nutrientes.
(ETAPA: Clarifier_last_hour. Razonamiento: Registro detallado que ayudará a comprender el contexto de la investigación.)

Zendell APP — 11:03
¿Qué planeas hacer entre las 11:03 y las 12:03, Elena?
(ETAPA: ask_next_hour. Razonamiento: Consultar el plan a corto plazo para complementar el análisis de la actividad.)

Elena — 11:04
Voy a realizar un nuevo set de experimentos para comparar los efectos de distintas concentraciones.
(ETAPA: Clarifier_next_hour. Razonamiento: Se pide detallar la planificación para prever necesidades de ajuste.)

Zendell APP — 11:04
¿Qué concentraciones o variables específicas piensas modificar en el nuevo set?
(ETAPA: Clarifier_next_hour. Razonamiento: Profundizar en la estrategia para un análisis preciso.)

Elena — 11:05
Modificaré la concentración de aminoácidos y mediré la respuesta en la proliferación celular en distintos intervalos.
(ETAPA: Clarifier_next_hour. Razonamiento: Información detallada que cierra el registro de la acción futura.)

Zendell APP — 11:05
Gracias, Elena. Toda la información ha sido registrada. ¡Quedo a tu disposición para cualquier consulta futura!
(ETAPA: Final. Razonamiento: Cierre del flujo con confirmación de la recolección completa de datos.)


## Ejemplos flujo NO feliz: 
 Cada ejemplo incluye el escenario problemático, el razonamiento interno del sistema, la predicción del fallo y la respuesta de redirección que permite reorientar al usuario y recabar los datos necesarios. Vamos a verlo:

Ejemplo 1: Usuario Evasivo en el Registro de Perfil
Zendell APP — 08:00
¡Hola! Soy Zendell, un sistema multiagente diseñado para asistirte. Para conocerte mejor, necesito saber: ¿cuál es tu nombre, ocupación, gustos y metas? (ETAPA: ask_profile. Razonamiento: Solicitar datos esenciales para personalizar la experiencia.)

Usuario (Sofía) — 08:01
No quiero compartir esos datos, es muy personal.
(Escenario Fallido: Respuesta evasiva. Predicción: El usuario evita dar información clave.)

Zendell APP — 08:02
Entiendo tu preocupación, Sofía. Es importante contar con estos datos para poder ofrecerte recomendaciones y recordatorios personalizados que realmente te ayuden. Puedes compartir simplemente tu nombre y a qué te dedicas, y más adelante podemos profundizar en gustos y metas cuando te sientas cómoda. ¿Qué opinas? (ETAPA: Redirección en ask_profile. Razonamiento: Explicar el uso de la información y ofrecer compartir datos parciales para iniciar el proceso.)

Sofía — 08:03
Bueno, me llamo Sofía y trabajo en atención al cliente.
(Resultado: Se recogen datos básicos y se reorienta al usuario hacia el flujo correcto.)

Ejemplo 2: Usuario Responde de Forma Vaga y Poco Detallada
Zendell APP — 12:00
¡Hola! Soy Zendell. ¿Qué hiciste entre las 11:00 y las 12:00? (ETAPA: ask_last_hour. Razonamiento: Recopilar datos de la actividad reciente.)

Usuario (Roberto) — 12:01
Ah, nada en particular.
(Escenario Fallido: Respuesta vaga. Predicción: No se obtiene información valiosa para análisis.)

Zendell APP — 12:02
Roberto, para entender mejor tu día y poder ayudarte de manera efectiva, me gustaría que me cuentes al menos una actividad específica o alguna tarea que realizaste, por mínima que sea. ¿Podrías darme algún detalle, aunque sea breve? (ETAPA: Clarifier_last_hour. Razonamiento: Incentivar una respuesta más detallada explicando la importancia de la información.)

Roberto — 12:03
Bueno, estuve revisando algunos correos y haciendo unas llamadas.
(Resultado: Se logra pasar de una respuesta vaga a una más informativa, permitiendo continuar el flujo.)

Ejemplo 3: Usuario Envía Respuestas Confusas o Fuera de Contexto
Zendell APP — 16:00
¡Hola! Soy Zendell. ¿Cuál es tu nombre y a qué te dedicas? (ETAPA: ask_profile. Razonamiento: Solicitar datos esenciales para el perfil.)

Usuario (Diego) — 16:01
¿Por qué tienen que saber eso? Además, la vida es como un sueño, ¿no crees?
(Escenario Fallido: Respuesta confusa y fuera de contexto. Predicción: El usuario se desvía del objetivo y genera ambigüedad.)

Zendell APP — 16:02
Diego, entiendo que pueda parecer invasivo, pero estos datos nos ayudan a ofrecerte un servicio personalizado y adaptado a tus necesidades. Solo necesito saber tu nombre y en qué área trabajas para empezar. ¿Podrías compartir esa información? (ETAPA: Redirección en ask_profile. Razonamiento: Reencauzar la conversación explicando la finalidad y simplificando la solicitud.)

Diego — 16:03
Está bien, me llamo Diego y soy diseñador de experiencia de usuario.
(Resultado: Se redirige la conversación y se obtienen los datos básicos para continuar el flujo.)

Ejemplo 4: Usuario Ignora la Pregunta Sobre la Actividad Pasada
Zendell APP — 10:00
¡Hola! Soy Zendell. ¿Qué hiciste entre las 09:00 y las 10:00? (ETAPA: ask_last_hour. Razonamiento: Recopilar información sobre la actividad reciente.)

Usuario (Martina) — 10:01
Mmm...
(Escenario Fallido: No respuesta o respuesta muy corta. Predicción: Falta de información sobre la actividad pasada.)

Zendell APP — 10:02
Martina, para poder ayudarte mejor y registrar tus actividades, necesito al menos un detalle de lo que hiciste en la última hora. ¿Podrías indicarme alguna actividad, por mínima que sea? (ETAPA: Clarifier_last_hour. Razonamiento: Incentivar la participación ofreciendo una solicitud concreta y explicando su utilidad.)

Martina — 10:03
Ok, estuve leyendo algunos artículos de tecnología.
(Resultado: Se consigue una respuesta que permite continuar el flujo de análisis.)

Ejemplo 5: Usuario Responde Incompletamente en la Planificación Futura
Zendell APP — 14:00
¡Hola! Soy Zendell. ¿Qué planeas hacer entre las 14:00 y las 15:00? (ETAPA: ask_next_hour. Razonamiento: Recoger información sobre la actividad futura para planificar el seguimiento.)

Usuario (Jorge) — 14:01
No sé...
(Escenario Fallido: Respuesta incompleta o indecisa. Predicción: No se obtiene información sobre la planificación futura.)

Zendell APP — 14:02
Jorge, contar con tus planes, aunque sean pequeños, me ayuda a orientarte mejor y ofrecerte recordatorios o sugerencias útiles. ¿Podrías decirme al menos si tienes alguna tarea pendiente o algo que planeas revisar? (ETAPA: Clarifier_next_hour. Razonamiento: Reorientar al usuario enfatizando el beneficio de la información para su propio progreso.)

Jorge — 14:03
Creo que voy a revisar unos correos y planificar el resto del día.
(Resultado: Se transforma la respuesta indecisa en un compromiso de acción concreta, permitiendo seguir con el flujo.)

## 6. Roadmap / Próximos Pasos
- **Testeo y analisis de dato de multiples conversaciones a lo largo de varios días
- ** Definir momento de conocimiento alto sobre el usuario para aportar ya con recomendacione y consejos personalizados de alto nivel de eficiencia
- **Integración con WhatsApp y Email**: Ya en proceso para llegar a más canales.  
- **Agente Bibliotecario**: Para manejar el contexto y el historial en mayor detalle.  
- **Optimización y Nuevos Nodos**: Añadir más agentes especializados (por ejemplo, agente de hábitos saludables, agente de gestión financiera).
- 
https://www.mermaidchart.com/raw/e3f8fb68-0d1e-4097-bc9c-4302d118bfe8?theme=light&version=v0.1&format=svg

¿Deberia reahacer toda la arquitectura?
