"""APScheduler job for the ambulance simulation (F-26). Started only when SIMULATION_ENABLED=true."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import ambulance

TICK_S = 2


def start() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        ambulance.tick,
        "interval",
        seconds=TICK_S,
        kwargs={"dt": float(TICK_S)},
        max_instances=1,
        coalesce=True,
        id="ambulance_sim",
    )
    scheduler.start()
    return scheduler
