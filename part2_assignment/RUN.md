
# How to Run This Project

This project uses Python 3 and requires the `scipy` and `networkx` libraries.

## 1. Installation

Install the required dependencies:
```sh
pip install scipy networkx
```

## 2\. Run All Automated Tests

This is the fastest way to verify the project. It will discover and run all tests in the `tests/` folder (`test_factory.py` and `test_belts.py`).

```sh
python run_samples.py
```

*(Alternatively, you can use the built-in unittest discover command: `python -m unittest discover tests`)*

## 3\. Manual Execution (PowerShell)

To run the solvers individually and see the JSON output in your terminal.

**Run the Factory Solver:**

```powershell
Get-Content .\factory_input.json | python .\factory\main.py
```

**Run the Belts Solver:**

```powershell
Get-Content .\belts_input.json | python .\belts\main.py
```

## 4\. Manual Execution (Linux / macOS / Git Bash)

**Run the Factory Solver:**

```sh
python factory/main.py < factory_input.json
```

**Run the Belts Solver:**

```sh
python belts/main.py < belts_input.json
```

## 5\. Verify Solution Files

You can use the `verify_*.py` scripts to check a solution file against an input file.

**Verify Factory:**

```powershell
# First, create an output file
Get-Content .\input.json | python .\factory\main.py > factory_output.json

# Then, verify it
python .\verify_factory.py .\input.json .\factory_output.json
```

**Verify Belts:**

```powershell
# First, create an output file
Get-Content .\belts_input.json | python .\belts\main.py > belts_output.json

# Then, verify it
python .\verify_belts.py .\belts_input.json .\belts_output.json
```

## 6\. Generate New Test Cases

You can pipe the generator scripts directly into the solvers to test new, random problems.

```powershell
# Test a new random factory
python .\gen_factory.py | python .\factory\main.py

# Test a new random belt graph
python .\gen_belts.py | python .\belts\main.py
```

```
```