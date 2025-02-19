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

### **5. tests/**  
- Pruebas del sistema (por ejemplo, usando `pytest`).  

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
  3. **Recommender** → genera consejos o próximos pasos.  

### **5. Persistencia**  
- Todo se guarda en MongoDB: desde datos de usuario hasta logs de conversación, permitiendo rastrear el historial y mejorar la experiencia.  

## 5. Funcionamiento en la Práctica

Imagina que ZENDELL te pregunta cada hora cosas como:  
- “¿Cómo te fue en tu última tarea?”  
- “¿Has comido recientemente?”  
- “¿Necesitas un resumen de tus pendientes?”  

Dependiendo de tus respuestas, el analizador deduce tu estado de ánimo o hábitos, y el recomendador te da sugerencias concretas (“Tómate un descanso de 5 minutos”, “Revisa tu lista de pendientes antes de comer”, etc.).  

## 6. Roadmap / Próximos Pasos

- **Integración con WhatsApp y Email**: Ya en proceso para llegar a más canales.  
- **Agente Bibliotecario**: Para manejar el contexto y el historial en mayor detalle.  
- **Optimización y Nuevos Nodos**: Añadir más agentes especializados (por ejemplo, agente de hábitos saludables, agente de gestión financiera).
- 
https://www.mermaidchart.com/raw/e3f8fb68-0d1e-4097-bc9c-4302d118bfe8?theme=light&version=v0.1&format=svg
