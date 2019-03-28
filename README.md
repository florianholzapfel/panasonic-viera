# panasonic-viera

## UPDATE (2019-03-28)

Pincode and encryption support has been added for newer TV models circa 2019. For example, the "FZ" Panasonic models. These new models require pincode authentication and communication is now encapsulated in AES-CBC-128 encryption with HMAC-SHA-256. See issue https://github.com/florianholzapfel/panasonic-viera/issues/9

## Usage

### Code

#### Examples

##### Increase Volume By 1

```python
import panasonic_viera
rc = panasonic_viera.RemoteControl("<HOST>")
volume = rc.get_volume()
rc.set_volume(volume + 1)
```

##### Send EPG Key

```python
import panasonic_viera
rc = panasonic_viera.RemoteControl("<HOST>")
rc.send_key(panasonic_viera.Keys.epg)
```

### Command Line

This command line starts a [REPL](https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop) to the TV. Therefore it is mainly used testing purposes and not for automating the TV.

```bash
usage: panasonic_viera [-h] [--verbose] host [port]

Remote control a Panasonic Viera TV.

positional arguments:
  host        Address of the Panasonic Viera TV
  port        Port of the Panasonic Viera TV. Defaults to 55000.

optional arguments:
  -h, --help  show this help message and exit
  --verbose   debug output
```
