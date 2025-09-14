import rich.console
import rich.table
import sys
import os
import subprocess
from . import scan
from . import db
import steam.client
import steam.enums

console = rich.console.Console()
options = []
sc = None

def steam_client():
    global sc
    if sc is None:
        sc = steam.client.SteamClient()
        
        if sc.anonymous_login() != steam.enums.EResult.OK:
            raise RuntimeError("Failed to login to Steam anonymously")
    return sc

def option(title):
    def decorator(function):
        options.append((title, function))
        return function
    return decorator

@option("Inspect volumes")
def option_show_volumes():
    with db.session() as session:
        volumes = session.query(db.Volume).all()
        choice = picker("Select volume", [f"{v.label or 'No Label'} ({len(v.applications)})" for v in volumes], True)

        if choice is None:
            return
        
        volume = volumes[choice]

        while True:
            choice = picker(f"{volume.label or 'No Label'} - {len(volume.applications)} applications", ["List applications", "Rescan volume"], True)

            if choice is None:
                return
            elif choice == 0:
                console.clear()
                console.print(f"[green]Shura[/green]")
                console.print(f"[blue]Volume {volume.label or 'No Label'}[/blue]")

                table = rich.table.Table(show_header=True, header_style="bold magenta")
                table.add_column("AppID", style="dim", width=12)
                table.add_column("Name")
                for app in volume.applications:
                    table.add_row(str(app.appid), app.name)
                
                console.print(table)
                console.input("Press Enter to continue...")
            elif choice == 1:
                scanned = False

                info = scan.Scan.volume_available(volume.id)

                if info:
                    apps, depots = scan.Scan(info[0]).scan()
                    console.print(f"[green]Rescan complete![/green] Found [cyan]{apps}[/cyan] applications and [cyan]{depots}[/cyan] depots.")
                else:
                    console.print(f"[red]Volume {volume.label or 'No Label'} not found![/red] Attach volume {volume.id} and try again.")
                console.input("Press Enter to continue...")

@option("Inspect applications")
def option_inspect_applications():
    app = app_picker("Find application")

    if not app:
        return

    while True:
        choice = picker(f"Application {app.name} ({app.appid}) on {app.volume.label or 'No Label'}", ["Install now", "Check for updates"], True)

        if choice is None:
            return
        elif choice == 0:
            info = scan.Scan.volume_available(app.volume.id)

            if not info:
                console.print(f"[red]Volume {app.volume.label or 'No Label'} not found![/red] Attach volume {app.volume.id} and try again.")
            else:
                console.print(f"[green]Launching Steam...[/green]")
                subprocess.Popen(["C:\\Program Files (x86)\\Steam\\steam.exe", "-install", os.path.join(info[0] + "\\", app.location)])

            console.input("Press Enter to continue...")
        elif choice == 1:
            sc = steam_client()

            with db.session() as session:
                refresh = session.get(db.Application, app.id)
                appinfo = sc.get_product_info(apps=[refresh.appid])['apps']

                if not appinfo or refresh.appid not in appinfo:
                    console.print(f"[red]Failed to fetch app info from Steam.[/red]")
                else:
                    for manifest in refresh.manifests:
                        try:
                            if (
                                str(manifest.depot) in appinfo[refresh.appid]['depots'] and
                                manifest.manifest != appinfo[refresh.appid]['depots'][str(manifest.depot)]['manifests']['public']['gid']
                            ):
                                console.print(f"[yellow]Depot {manifest.depot} has an update available.[/yellow]")
                                continue
                            else:
                                console.print(f"[green]Depot {manifest.depot} is up to date.[/green]")
                        except Exception as e:
                            console.print(f"[red]Error checking depot {manifest.depot}: {e}[/red]")

                console.input("Press Enter to continue...")

@option("Scan volumes for applications")
def option_scan():
    volumes = scan.Scan.volumes()
    choice = picker("Select volume", [f"{v[0]} ({v[1]})" for v in volumes], True)

    if not choice:
        return

    volume = volumes[choice][0]
    apps, depots = scan.Scan(volume).scan()
    console.print(f"[green]Scan complete![/green] Found [cyan]{apps}[/cyan] applications and [cyan]{depots}[/cyan] depots.")
    console.input("Press Enter to continue...")

@option("Exit")
def option_exit():
    sys.exit(0)

def app_picker(title):
    with db.session() as session:
        while True:
            console.clear()
            console.print(f"[green]Shura[/green]")
            if title:
                console.print(f"[blue]{title}[/blue]")
            console.print(f"[cyan]{session.query(db.Application).count()} applications[/cyan]")
            search = console.input("Search for application name or enter ID: ")

            if not search:
                return None

            if search.isdigit():
                app = session.query(db.Application).filter_by(appid=int(search)).first()
                if app:
                    return app

            apps = session.query(db.Application).filter(db.Application.name.ilike(f"%{search}%")).all()
            if apps:
                result = picker(f"Select application", [f"[cyan]{a.name} ({a.appid})[/cyan] on [cyan]{a.volume.label}[/cyan]" for a in apps], True)

                if result is not None:
                    return apps[result]
                else:
                    continue

            console.print("[red]No application found.[/red]")
            console.input("Press Enter to continue...")

def picker(title, options, allow_cancel=False):
    while True:
        console.clear()

        console.print(f"[green]Shura[/green]")
        if title:
            console.print(f"[blue]{title}[/blue]")
        
        table = rich.table.Table(show_header=False)
        for i, option in enumerate(options):
            table.add_row(f"[cyan]{i+1}[/cyan]", option)
        
        if allow_cancel:
            table.add_row(f"[cyan]{len(options)+1}[/cyan]", "Cancel")

        console.print(table)

        choice = console.input("Choose an option: ")

        if choice.isdigit():
            choice = int(choice) - 1
            if 0 <= choice < len(options):
                return choice
            elif allow_cancel and choice == len(options):
                return None
            else:
                console.print("[red]Invalid choice.[/red]")
        else:
            console.print("[red]Invalid input. Please enter a number.[/red]")

def menu():
    while True:
        choice = picker("Main menu", [title for title, func in options])
        options[choice][1]()

menu()