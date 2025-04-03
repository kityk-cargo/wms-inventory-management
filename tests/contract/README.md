# Contract Testing for Inventory Management Service

This directory contains contract tests for the WMS Inventory Management Service, which verify that the service adheres to its contracts with other services.

## What are Contract Tests?

Contract tests verify that an API provider correctly implements the API expected by its consumers. These tests use contract files (Pacts) that define the interactions between consumers and providers.

## Provider Contract Tests

The `test_inventory_management_contracts.py` file contains provider contract tests that verify the Inventory Management Service correctly fulfills the contracts defined by its consumers.

### How It Works

1. The test uses the Pact Verifier to load contract files (Pacts) from the specified directory.
2. It spins up the Inventory Management Service using Uvicorn on a local port.
3. For each interaction defined in the contracts, it:
   - Sets up the provider state using the `provider_states` endpoint
   - Makes the request defined in the contract to the running service
   - Verifies the response matches what's expected in the contract

### Running the Tests

You can run the contract tests with:

```bash
# Set environment variable for custom Pact directory (optional)
export PACT_DIR_PATH=/path/to/your/pacts

# Run tests with pytest
pytest tests/contract -v
```

### Configuration

- The location of the Pact files is controlled by the `PACT_DIR_PATH` environment variable.
- The default location is `../wms-contracts/pact/rest/wms_inventory_management`.

## Provider States

Provider states are used to set up the necessary test data before each interaction is verified. The `provider_states` endpoint in `test_inventory_management_contracts.py` handles setting up these states.

Currently implemented states:

- `products exist`: Sets up sample product data matching what's expected in the contract
- `no products exist`: Sets up an empty product list

## Adding New Provider States

To add a new provider state:

1. Add a new condition in the `provider_states` function
2. Implement the setup logic for your state
3. Ensure the consumer tests generate contracts with the appropriate provider state

## CI/CD Integration

These tests should be run as part of your CI/CD pipeline to ensure that API changes don't break existing contracts with consumers. 