const express = require("express");
const app = express();

function fibo(n) {
  if (n < 2) return 1;
  else return fibo(n - 2) + fibo(n - 1);
}

app.get("/alive", (req, res) => res.send("Alive!"));
app.get("/", (req, res) => {
  res.send(fibo(req.query.fiboIdx || 40).toString());
});

app.listen(3000, () => console.log(`YoYo server listening on port 3000!`));
