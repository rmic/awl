
from awl import determine_location
from gcal import get_calendar_service, update_working_location, get_working_location
from rich.console import Console
import typer
from datetime import datetime, timedelta
import yaml
console = Console()
app = typer.Typer()
SCOPES = ['https://www.googleapis.com/auth/calendar']

@app.command()
def detect_location(location_map_file: str):
    location_map = yaml.safe_load(open(location_map_file))
    location = determine_location(location_map)
    if location == "HOME":
        console.print("You are currently at: [green]🏠 Home[/green]")
    elif location == "OFFICE":
        console.print("You are currently at: [green]🕋 Office[/green]")
    else:
        console.print("You are currently at: [red]❓ Unknown[/red]")



@app.command()
def auto_update_location(location_map_file: str= "locations_map.yaml", token_file: str = "token.json", credentials_file: str = "credentials.json"):
    location_map = yaml.safe_load(open(location_map_file))
    location = determine_location(location_map)
    today = datetime.today().strftime('%Y-%m-%d')
    service = get_calendar_service(token_file, credentials_file, SCOPES)
    try:
        current_working_location = get_working_location(today, service)

        if location in ["HOME", "OFFICE"] and current_working_location != location:
            console.print(f"Updating location from [yellow] {current_working_location} [/yellow] to: [green] {location}[/green]")
            update_working_location(today, location, service)
        else:
            console.print(f"Location not updated : current location: [yellow] {current_working_location}[/yellow] new location: [yellow] {location}[/yellow]")
    except Exception as e:
        console.print(f"Error updating location: [red] {e}[/red]")

@app.command()
def set_next_week(schema:str, token_file: str = "token.json", credentials_file: str = "credentials.json"):
    service = get_calendar_service(token_file, credentials_file, SCOPES)

    locations = schema.split(",")
    loc_map = {
        "H":"HOME",
        "O":"OFFICE"
    }

    next_monday = datetime.today() + timedelta(days=(0 - datetime.today().weekday()) + 7)
    for i in range(5):
        date = (next_monday + timedelta(days=i)).strftime("%Y-%m-%d")
        location = loc_map.get(locations[i], None)
        if location:
            #console.print(f"Setting location for {date} to {location}")
            update_working_location(date, location, service)


if __name__ == '__main__':
    app()