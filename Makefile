# This lists all the packages that are hosted in this mono-repo.
DIRS = exdrf exdrf-al exdrf-pd exdrf-qt exdrf-dev

# These are all python files in all the repository (including venv ones).
PYTHON_FILES := $(wildcard *.py)


# The target runs autoflake on all the python files in the repository.
# It removes all unused imports.
aflake: $(PYTHON_FILES)
	autoflake \
		--in-place \
		--remove-all-unused-imports \
		--recursive \
		--exclude ".vscode,playground,venv,legacy" .



# ======================== [ Windows-specific targets ] ========================
ifeq ($(OS),Windows_NT)

# Set the shell that will execute the commands.
SHELL = cmd.exe


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
delint: aflake
	@for %%d in ($(DIRS)) do ( \
		pushd "$(CURDIR)\%%d" && \
		autoflake --in-place --remove-all-unused-imports --recursive . && \
		python -m isort . && \
		python -m black . && \
		popd)

# Collects all the .ui files.
UI_FILES := $(shell powershell -Command "Get-ChildItem '$(MODULE_NAME)' -Recurse -Filter '*.ui' | ForEach-Object { $$_.FullName }")


# ========================= [ Linux-specific targets ] =========================
else

# Set the shell that will execute the commands.
SHELL = /bin/bash


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
delint: aflake
	@for dir in $(DIRS); do \
		cd $$dir && autoflake --in-place --remove-all-unused-imports --recursive .; \
		cd $$dir && python -m isort .; \
		cd $$dir && python -m black --quiet .; \
		cd - > /dev/null; \
	done


# Collects all the .ui files.
UI_FILES := $(shell find $(MODULE_NAME) -type f -name '*.ui')

endif
# ==================== [ End of platform-specific targets ] ====================


# All the files generated from the .ui files.
PY_UI_FILES := $(UI_FILES:.ui=_ui.py)


# Define the .ui to _ui.py conversion rule
%_ui.py: %.ui exdrf-qt/exdrf_qt/scripts/gen_ui_file.py
	python -m exdrf_qt.scripts.gen_ui_file $< $@


# Add a dependency rule to regenerate _ui.py files only if .ui files change
build-ui: $(PY_UI_FILES) delint
