# Sample project — deliberately breakable

A tiny one-page website for a bakery. `lastgood-config.json` is the
LastGood check setup for this folder (read directly from the project):

- the page still opens as a web page
- the words "Sunny Day Bakery" are still in it
- the phone number "555-0100" is still in it

Good change to try: change "Fresh bread every morning." wording.
Breaking change to try: rename the bakery or delete the phone line —
the next tested step should be FAIL, and /lastgood blame should name it.
