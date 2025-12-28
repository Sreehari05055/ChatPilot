from pathlib import Path
import argparse
import subprocess
import sys


def run_configurator():
    # Execute the configurator as a module so imports like `app` resolve
    project_root = Path(__file__).resolve().parent
    module_name = "scripts.configure"
    subprocess.run([sys.executable, "-m", module_name], check=True, cwd=str(project_root))


def run_admin_configurator():
    # Execute the admin CLI as a module so package imports are available
    project_root = Path(__file__).resolve().parent
    module_name = "scripts.admin_manage"
    subprocess.run([sys.executable, "-m", module_name], check=True, cwd=str(project_root))


def main():
    parser = argparse.ArgumentParser(description="ChatPilot runner")
    parser.add_argument('--admin-config', action='store_true', help='Interactively update configuration')
    parser.add_argument("--configure", action="store_true", help="Run interactive configuration wizard and exit")
    parser.add_argument("--dev", action="store_true", help="Run development server (uvicorn) for local testing")
    parser.add_argument("--host", default="0.0.0.0", help="Host for the FastAPI server")
    parser.add_argument("--port", default=8000, type=int, help="Port for the FastAPI server")
    args = parser.parse_args()

    if args.configure:
        run_configurator()
        return

    if args.admin_config:
        run_admin_configurator()
        return

    if args.dev:
        # Local development runner (kept for convenience)
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        from app import create_app

        app = create_app()

        origins = [
            "http://localhost:5173",  # Vite dev server
        ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        uvicorn.run(app, host=args.host, port=args.port)
        return

    # Production guidance: expose the ASGI `app` from `asgi.py` and run with an ASGI server
    print("Production runner: use an ASGI server to run the app, for example:")
    print()
    print("  uvicorn asgi:app --host 0.0.0.0 --port 8000 --workers 4")
    print("  gunicorn -k uvicorn.workers.UvicornWorker -w 4 asgi:app")
    print()
    print("To run interactively for local development: `python main.py --dev`")


if __name__ == '__main__':
    main()

