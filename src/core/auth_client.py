"""Client d'authentification RFC 8628 et de gestion des quotas pour la CLI ezShell."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.proxy_client import TokenStore, _client_version, api_url

console = Console()


class AuthClient:
    def __init__(self, base_url: Optional[str] = None, store: Optional[TokenStore] = None):
        self.base_url = (base_url or api_url()).rstrip("/")
        self.store = store or TokenStore()

    def _post(self, path: str, payload: dict, token: Optional[str] = None) -> Tuple[int, dict]:
        headers = {
            "content-type": "application/json",
            "user-agent": f"ezshell-cli/{_client_version()}",
        }
        if token:
            headers["authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                return resp.status, data
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8", errors="replace"))
            except Exception:
                data = {"error": f"HTTP {exc.code}"}
            return exc.code, data
        except Exception as exc:
            return 0, {"error": str(exc)}

    def _get(self, path: str, token: Optional[str] = None) -> Tuple[int, dict]:
        headers = {
            "user-agent": f"ezshell-cli/{_client_version()}",
        }
        if token:
            headers["authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base_url + path, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                return resp.status, data
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8", errors="replace"))
            except Exception:
                data = {"error": f"HTTP {exc.code}"}
            return exc.code, data
        except Exception as exc:
            return 0, {"error": str(exc)}

    def login(self) -> int:
        """Déclenche le flux RFC 8628 Device Authorization pour connecter le terminal."""
        current_token = self.store.load(self.base_url)
        console.print("[dim]Initialisation de la connexion sécurisée...[/dim]")

        status, data = self._post("/api/v1/auth/device/code", {}, current_token)
        if status != 200 or "device_code" not in data:
            console.print(f"[bold red]✘ Erreur serveur lors de l'authentification :[/bold red] {data.get('error', status)}")
            return 1

        device_code = data["device_code"]
        user_code = data["user_code"]
        verify_url = data["verification_uri"]
        complete_url = data.get("verification_uri_complete", f"{verify_url}?user_code={user_code}")
        interval = max(2, int(data.get("interval", 3)))
        expires_in = int(data.get("expires_in", 900))
        new_device_token = data.get("device_token")

        if new_device_token:
            self.store.save(self.base_url, new_device_token)

        # Affichage du panneau
        panel_content = (
            f"[bold white]1. Rendez-vous sur la page d'activation :[/bold white]\n"
            f"   [bold cyan underline]{complete_url}[/bold cyan underline]\n\n"
            f"[bold white]2. Code d'activation à valider :[/bold white]\n"
            f"   [bold yellow text-2xl]{user_code}[/bold yellow text-2xl]\n\n"
            f"[dim]Ce code expire dans {expires_in // 60} minutes. Compatible environnements headless/SSH.[/dim]"
        )
        console.print(Panel(panel_content, title="🔐 Connexion ezShell (RFC 8628)", border_style="cyan"))

        # Tenter d'ouvrir le navigateur
        try:
            webbrowser.open(complete_url)
        except Exception:
            pass

        # Polling RFC 8628
        start_time = time.time()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("[cyan]En attente de votre approbation dans le navigateur...", total=None)

            while time.time() - start_time < expires_in:
                time.sleep(interval)
                poll_status, poll_data = self._post(
                    "/api/v1/auth/device/token",
                    {"device_code": device_code},
                    None,
                )

                if poll_status == 200:
                    user_info = poll_data.get("user", {})
                    user_desc = user_info.get("email") or user_info.get("id", "compte")
                    plan = user_info.get("plan", "free").capitalize()
                    console.print(
                        f"\n[bold green]✔ Connexion réussie ![/bold green] "
                        f"Terminal associé à [bold]{user_desc}[/bold] (Plan: [bold cyan]{plan}[/bold cyan])."
                    )
                    return 0

                err = poll_data.get("error")
                if err == "authorization_pending":
                    continue
                elif err == "slow_down":
                    interval += 2
                    continue
                elif err in ("access_denied", "expired_token"):
                    console.print(f"\n[bold red]✘ Connexion annulée :[/bold red] {poll_data.get('error_description', err)}")
                    return 1
                else:
                    console.print(f"\n[bold red]✘ Erreur inattendue :[/bold red] {poll_data.get('error_description', err)}")
                    return 1

        console.print("\n[bold red]✘ Délai d'attente expiré.[/bold red] Veuillez relancer 'ezsh login'.")
        return 1

    def logout(self) -> int:
        """Déconnecte le terminal et révoque le jeton local."""
        token = self.store.load(self.base_url)
        if not token:
            console.print("[yellow]Aucune session active trouvée sur ce terminal.[/yellow]")
            return 0

        try:
            self._post("/api/v1/auth/device/revoke", {}, token)
        except Exception:
            pass

        self.store.clear()
        console.print("[bold green]✔ Vous avez été déconnecté avec succès.[/bold green] Les jetons locaux ont été supprimés.")
        return 0

    def usage(self) -> int:
        """Affiche les quotas consommés, restants et la date de renouvellement."""
        token = self.store.load(self.base_url)
        status, data = self._get("/api/v1/usage", token)

        if status == 401 or status == 403:
            console.print(f"[bold red]✘ Accès refusé :[/bold red] {data.get('message', 'Non autorisé')}")
            return 1
        if status != 200:
            console.print(f"[bold red]✘ Impossible de récupérer vos quotas :[/bold red] {data.get('error', status)}")
            return 1

        acc_type = data.get("account_type", "anonymous")
        user = data.get("user") or {}
        quota = data.get("quota") or {}
        tier = quota.get("tier", "anonymous")
        used = quota.get("used_today", 0)
        limit = quota.get("daily_limit")
        remaining = quota.get("remaining_today")
        reset_at = quota.get("reset_at")

        is_unlimited = tier == "unlimited" or limit is None

        # Formatage de l'affichage
        lines = []
        if acc_type == "registered" and user:
            user_label = user.get("email") or user.get("github_login") or user.get("id")
            lines.append(f"[bold white]Compte :[/bold white] [cyan]{user_label}[/cyan]")
        else:
            lines.append("[bold white]Compte :[/bold white] [dim]Anonyme (Mode découverte)[/dim]")

        lines.append(f"[bold white]Plan :[/bold white] [bold cyan]{tier.capitalize()}[/bold cyan]")
        lines.append("")

        if is_unlimited:
            lines.append("[bold white]Consommation aujourd'hui :[/bold white] [bold green]Illimitée[/bold green]")
        else:
            pct = min(100, int((used / limit) * 100)) if limit else 0
            bar_color = "red" if pct > 85 else "yellow" if pct > 60 else "green"
            lines.append(f"[bold white]Consommation aujourd'hui :[/bold white] [{bar_color}]{used} / {limit}[/{bar_color}] requêtes ({pct}%)")
            lines.append(f"[bold white]Requêtes restantes :[/bold white] [bold]{remaining}[/bold]")

        if reset_at:
            lines.append(f"[bold white]Prochain renouvellement :[/bold white] [dim]{reset_at} (Minuit UTC)[/dim]")

        if acc_type == "anonymous":
            lines.append("\n[italic yellow]💡 Astuce : Connectez-vous avec 'ezsh login' pour augmenter votre quota gratuitement ![/italic yellow]")

        console.print(Panel("\n".join(lines), title="📊 Quotas et Utilisation ezShell", border_style="cyan"))
        return 0
