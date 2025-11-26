# Orcos en Automata Celular

Simulacion sencilla de orcos que se desplazan, pelean y evolucionan sobre una cuadricula. El bucle de simulacion y las reglas viven en Python y la visualizacion usa Pygame para mostrar el mapa en tiempo real.

## Como correrlo

```bash
python -m venv .venv

.venv\\Scripts\\activate # Windows
# o
source .venv/bin/activate # Unix/MacOS

pip install -e .

orc-automata
# o
python -m orc_automata.main
```

Teclas rapidas:
- `Esc` o cerrar ventana: salir
- `Space`: pausar/reanudar
- `R`: reiniciar con la misma semilla
- El reloj corre mas lento (`tick_rate=6`) para observar mejor la simulacion.
- El fondo de cada celda muestra el ambiente: marron = seco (penaliza), cian = humedo (ayuda ligeramente).
- Los orcos se dibujan con sprites (`assets/orc1.png`, `orc2.png`, `orc3.png`) escalados al tamano de celda; se toma solo el primer frame de cada sheet.
- El ambiente usa ruido suavizado y gradientes para formar zonas amplias de humedad/fertilidad coherentes; la semilla puede fijarse en `SimulationSettings`.
- Hay 3 biomas discretos con una ligera tinta de color, cada uno favorece una clase, penaliza otra y deja neutral la tercera.
- Las peleas ajustan estabilidad: si los combatientes son parejos hay escaramuzas no letales, y clases con poblacion muy baja evitan iniciar ataques.
- Ambientes pesan mas: humedad/bioma influyen mas en energia y movimiento, asi que la raza afin a un bioma prospera mejor ahi y su bioma enemiga sufre mas.
- Grupos de la misma clase dan un pequeno soporte de energia, y un orco aislado rodeado por enemigos obtiene un bono de resistencia para intentar sobrevivir.
- Hay un virus de baja probabilidad que puede aparecer y propagarse; resta energia y debilita en combate mientras dura la infeccion.
- Orcos infectados se ven con un tinte morado para distinguirlos.
- HUD muestra contador por raza (C0/C1/C2) para seguir poblaciones.
- Existe un limite de poblacion global: al superarlo, cada orco tiene una probabilidad creciente de morir por sobrepoblacion, ayudando a estabilizar el ecosistema.
- Los orcos buscan habitats favorables: si estan en zonas malas (bioma/ambiente), sesgan su movimiento hacia celdas cercanas con mejor ambiente.
- Proteccion a razas en peligro: si una clase queda muy pequena, no la atacan y tiene bonus a reproduccion para evitar exterminios rapidos.
- Cada raza tiene rasgos base distintos: fuerza (C0 1.1x, C1 0.9x, C2 1x), agilidad (C0 0.95x, C1 1.1x, C2 1x) y resiliencia (C0 1x, C1 0.95x, C2 1.1x).
 - El bioma de la celda define la raza al nacer (C0 en bioma 0, C1 en bioma 1, C2 en bioma 2), haciendo que cada region genere su raza afin.

## Estructura

- `pyproject.toml`: dependencias y entrypoint.
- `src/orc_automata/config.py`: parametros del mundo y mutacion.
- `src/orc_automata/orc.py`: modelo de orcos y mutaciones.
- `src/orc_automata/environment.py`: cuadricula y manejo de celdas.
- `src/orc_automata/simulation.py`: reglas del automata y evolucion.
- `src/orc_automata/rendering/pygame_renderer.py`: ventana y dibujo con Pygame.
- `src/orc_automata/assets/`: sprites empaquetados para el renderer.
- `src/orc_automata/main.py`: bucle principal para lanzar la simulacion.
- Los orcos tienen `kind` (clase) y tienden a moverse en manada hacia otros de su clase; las peleas solo ocurren entre clases distintas.

## Como extender

- Ajusta `SimulationSettings` para cambiar tamanio del mapa, velocidad, energia, probabilidad de mutacion o reproduccion.
- Las reglas viven en `Simulation.step` y metodos privados; puedes agregar nuevos eventos (clanes, jerarquia) sin tocar el renderer.
- El renderer solo depende de la interfaz publica de `Simulation`, asi que puede reemplazarse por otra vista (por ejemplo una API o CLI) manteniendo el motor base.

## Como influye el ambiente

- Humedad (`humidity_at`): baja genera penalizacion de energia cada tick; alta da un pequeno bono. Tambien influye en la preferencia de movimiento.
- Fertilidad (`fertility_at`): determina cuanta energia se gana al forrajear y tambien atrae el movimiento hacia celdas mas ricas.
- El mapa mezcla ruido y gradientes verticales suavizados para crear regiones (zonas secas/vales humedos) visibles en el color de fondo.
- Mapa mas grande por defecto (64x40) y ambientes con parches mas amplios para ver regiones marcadas.
 - Cada celda pertenece a un bioma (3 tipos): si coincide con la clase del orco recibe un bono de energia leve; si es la bioma “enemiga” recibe una penalizacion leve; la tercera combinacion es neutral. Tambien influye en el movimiento.
