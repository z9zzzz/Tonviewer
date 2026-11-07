# Command-line interface

Installing the package creates the `Tonviewer` command. Use `Tonviewer --help` for the installed command's help text.

```bash
Tonviewer --version
Tonviewer --check-update
Tonviewer --price
Tonviewer --wallet UQ... --info
Tonviewer --wallet UQ... --transactions --limit 10
Tonviewer --transactions UQ... --action "received ton" --limit 20
Tonviewer --raw-transactions --wallet UQ... --limit 100 --offset 0 --sort desc
Tonviewer --hash EVENT_OR_TRANSACTION_HASH
Tonviewer --username durov
```

Short aliases include `-w` wallet, `-i` info, `-t` parsed transactions, `-r` raw v3 transactions, `-l` limit, `-a` action, `-H` hash, `-p` price, and `-u` username. `-t UQ...` can provide the address directly; `-w UQ... -t` also works. `--number N` selects a 1-based transaction row after filtering. `--offset` is for raw transaction pages; `--sort` accepts `asc` or `desc`.

`--json` requests JSON output where the command supports more than one output style. Wallet and compatibility commands already print JSON strings. The CLI uses your environment/configuration keys as described in [Configuration](configuration.md).
