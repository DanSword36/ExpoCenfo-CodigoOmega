# Avance del Proyecto

## 1. Información del Proyecto
**Vocal Mind**
- **Equipo:**

**Daniel Guzmán Hidalgo**
  
**Andy Arias Jiménez**

**Danny Arias Jiménez**

  **Roles**
- Daniel Guzmán Hidalgo	Encargado de APIs y Claves	Integración de APIs (STT/TTS), autenticación.
- Danny Arias Jiménez	Administrador de Base de Datos	Diseño, optimización y seguridad de la DB.
- Andy Arias Jiménez	Encargado de Servidores	Configuración, despliegue y escalabilidad.

## 2. Descripción y Justificación
- **Problema que se aborda:** Decidimos abordar un gran problema que ultimamente se esta enfrentando tanto en el pais como en el mundo la cual es la indecision de las personas las cuales no saben que hacer ya sea luego de salir del colegio o incluso ya de adultos
- **Importancia y contexto:** La indecisión sobre el futuro es un problema creciente que afecta tanto a jóvenes como a adultos. Muchas personas no saben qué camino tomar después del colegio o incluso ya en su etapa adulta. Este proyecto busca orientar y apoyar en ese proceso de decisión, ayudando a las personas a descubrir sus intereses y tomar decisiones con seguridad. Brindar esta guía es clave para formar individuos más enfocados, motivados y preparados para enfrentar sus desafíos.  
- **Usuarios/beneficiarios:**  Este proyecto está dirigido a jóvenes que están por terminar el colegio y no tienen claro qué camino seguir, así como a adultos que sienten dudas sobre su rumbo profesional o personal
- 

## 3. Objetivos del Proyecto
 **Objetivo General:**  
 -Brindar orientación y apoyo mediante una IA a personas indecisas sobre su futuro académico, profesional o personal, ayudándoles a tomar decisiones informadas y seguras que contribuyan a su desarrollo integral.
 
 **Objetivos Específicos:**
-Desarrollar una inteligencia artificial capaz de analizar intereses, habilidades y preferencias personales.
-Ofrecer recomendaciones personalizadas de carreras disponibles en nuestra universidad.
-Facilitar la toma de decisiones vocacionales mediante una plataforma accesible y confiable.
-Reducir los niveles de incertidumbre en los estudiantes al brindar orientación clara y adaptada a su perfil.

## 4. Requisitos Iniciales
- Lista breve de lo que el sistema debe lograr:  
  - Requisito 1: Consultar la base de datos de las carreras de la universidad para tomar deciciones asertivas
  - Requisito 2: El sistema debe permitir convertir voz a texto mediante una API, y enviar el texto resultante como prompt a la IA
  - Requisito 3: crear un avtar virtual que interactue con el usuario de manera mas amigable

## 5. Diseño Preliminar del Sistema

<img width="1536" height="1024" alt="ChatGPT Image 3 ago 2025, 22_45_05" src="https://github.com/user-attachments/assets/60f68e26-c590-4ebe-8c20-e0003a5726dc" />

- **Componentes previstos:**  
  - RaspberryPI 2 
  - Microfono y Pantalla 
  - LLM/API:  
    


## 6. Plan de Trabajo

| Semana | Actividades                                                                                                            |
| ------ | ---------------------------------------------------------------------------------------------------------------------- |
| 1      | - Definición del problema y objetivos del proyecto - Investigación sobre LLMs y APIs de voz a texto                    |
| 2      | - Selección de tecnologías - Diseño inicial de la interfaz                                                             |
| 3      | - Desarrollo del módulo de conversión de voz a texto                                                                   |
| 4      | - - Pruebas básicas del reconocimiento de voz                                                                          |
| 5      | - Integración con la API del modelo de lenguaje                                                                        |
| 6      | - Estructuración del prompt de recomendación                                                                           |
| 7      | - Pruebas internas con distintos perfiles de usuario<br>- Ajustes en recomendaciones y retroalimentación               |


- **Riesgos identificados y mitigaciones:**  
  **Riesgo 1:** Fallos en la conversión de voz a texto (por ruido, mala pronunciación o acento).
  **Mitigación:** Utilizar una API robusta con soporte para distintos acentos
  
  **Riesgo 2:** Recomendaciones imprecisas o poco relevantes por parte de la IA.
  **Mitigación:** Ajustar los prompts de entrada y entrenar al modelo con ejemplos específicos de perfiles vocacionales. Además, permitir retroalimentación del usuario para mejorar las       sugerencias.


