# This lists all the packages that are hosted in this mono-repo.
DIRS = exdrf \
    exdrf-al \
    exdrf-pd \
    exdrf-qt \
    exdrf-dev \
    exdrf-gen \
    exdrf-gen-al2qt \
    exdrf-gen-al2pd \
    exdrf-gen-al2at \
    exdrf-util \
    exdrf-xl \
    exdrf-gen-al2xl

# These are all python files in all the repository (including venv ones).
PYTHON_FILES := $(wildcard *.py)


# The target runs autoflake on all the python files in the repository.
# It removes all unused imports.
aflake: $(PYTHON_FILES)
	autoflake \
		--in-place \
		--remove-all-unused-imports \
		--recursive \
		--exclude ".vscode,playground,venv,venv-qt5,venv-qt6,legacy" .



# ======================== [ Windows-specific targets ] ========================
ifeq ($(OS),Windows_NT)

# Set the shell that will execute the commands.
SHELL = cmd.exe
SETENV = set

# Load environment variables from .env file
load-env:
	@echo Loading environment from .env file...
	@for /F "tokens=*" %%i in (.env) do ( \
		set "%%i" \
	)

# Run a command with environment variables loaded
with-env:
	@echo Loading environment from .env file...
	@for /F "usebackq tokens=1,* delims==" %%G in (.env) do ( \
		setlocal EnableDelayedExpansion && \
		set "line=%%G=%%H" && \
		if not "!line:~0,1!" == "#" ( \
			endlocal && set "%%G=%%H" \
		) else ( \
			endlocal \
		) \
	)


# Installs all the packages in the mono-repo into the current environment.
# This is suitable for production environments.
init:
	@for %%d in ($(DIRS)) do ( \
		pushd "$(CURDIR)\%%d" && pip install -e . && popd)


# Installs all the packages in the mono-repo into the current environment with
# dev dependencies.
init-d:
	@for %%d in ($(DIRS)) do ( \
		pushd "$(CURDIR)\%%d" && pip install -e .[dev] && popd)


# Runs all the tests in the mono-repo.
test:
	@for %%d in ($(DIRS)) do ( \
		echo Running tests in $(CURDIR)\%%d ... && \
		pushd "$(CURDIR)\%%d" && pytest . && popd)


# Checks the code style in all the packages in the mono-repo.
lint:
	@for %%d in ($(DIRS)) do ( \
		pushd "$(CURDIR)\%%d" && \
		python -m isort --check . && \
		python -m black --check --quiet . && \
		python -m pflake8 . && \
		popd)


# Fixes the code style in all the packages in the mono-repo.
delint: ui aflake
	@for %%d in ($(DIRS)) do ( \
		pushd "$(CURDIR)\%%d" && \
		python -m isort . && \
		python -m black . && \
		popd)

# Collects all the .ui files.
UI_FILES := $(shell python -c "import os; [print(os.path.relpath(os.path.join(root, f)).replace('\\', '/')) for root, _, files in os.walk('.') if 'venv' not in root for f in files if f.endswith('.ui')]")


# ========================= [ Linux-specific targets ] =========================
else

# Set the shell that will execute the commands.
SHELL = /bin/bash
SETENV = export

# Load environment variables from .env file
load-env:
	@echo "Loading environment from .env file..."
	@set -a && \
	source .env && \
	set +a


# Run a command with environment variables loaded
with-env:
	@echo "Loading environment from .env file..."
	@export $$(grep -v '^#' .env | xargs -d '\n')


# Installs all the packages in the mono-repo into the current environment.
# This is suitable for production environments.
init:
	@for dir in $(DIRS); do \
		cd $$dir && pip install -e .; \
		cd - > /dev/null; \
	done


# Installs all the packages in the mono-repo into the current environment with
# dev dependencies.
init-d:
	@for dir in $(DIRS); do \
		cd $$dir && pip install -e .[dev]; \
		cd - > /dev/null; \
	done


# Runs all the tests in the mono-repo.
# This is suitable for production environments.
test:
	@for dir in $(DIRS); do \
		cd $$dir && pytest; \
		cd - > /dev/null; \
	done


# Checks the code style in all the packages in the mono-repo.
lint:
	@for dir in $(DIRS); do \
		cd $$dir && python -m isort --check .; \
		cd $$dir && python -m black --check --quiet .; \
		cd $$dir && python -m pflake8 .; \
		cd - > /dev/null; \
	done


# Fixes the code style in all the packages in the mono-repo.
delint: ui aflake
	@for dir in $(DIRS); do \
		cd $$dir && python -m isort .; \
		cd $$dir && python -m black --quiet .; \
		cd - > /dev/null; \
	done


# Collects all the .ui files.
UI_FILES := $(shell find $(CURDIR) -type f -name '*.ui')

endif
# ==================== [ End of platform-specific targets ] ====================


# All the files generated from the .ui files.
PY_UI_FILES := $(UI_FILES:.ui=_ui.py)


# Define the .ui to _ui.py conversion rule
%_ui.py: %.ui exdrf-qt/exdrf_qt/scripts/gen_ui_file.py
	@echo "Generating $@ from $<..."
	python -m exdrf_qt.scripts.gen_ui_file $< $@


# Add a dependency rule to regenerate _ui.py files only if .ui files change
ui:
	python -m exdrf_qt.scripts.gen_ui_file gen "$(CURDIR)" --ex-dir-name "venv" --ex-dir-name "playground"


# Set the PYQTDESIGNERPATH environment variable to a path inside this directory
design:
	python -m exdrf_dev.cli run env:DESIGNER
