Smol
====

Smol is a static site generator written in Python. It has as few opinions as possible.

This started as a fork of [Makesite](https://github.com/sunainapai/makesite)

[MIT License](LICENSE.md)

Contents
--------

- [Smol](#smol)
  - [Contents](#contents)
  - [Usage](#usage)
  - [CLI](#cli)
  - [But Why?](#but-why)
  - [License](#license)


Usage
------------

Smol traverses the entire source directory, and will compile every `.html` file it finds there. It does this using Jinja2 templates, which get their variables from two places:

1. A global environment which you can populate by putting `smol.json` in the root of the source directory.
2. A page-specific header that looks like:

   ```
   <!-- var_one: foo -->
   <!-- var_two: bar -->
   ```

3. Finally, you can use the `list_files(filepath)` command to retrieve the urls and headers of other files at a specified path.

As an example:

*smol.json*
```
{
  "author": "Sunaina",
  "url": "www.sunaina-blog.example"
}
```

*posts/post_1.html*
```
<!-- title: My first blog post! -->
This is my first blog post.
```

*index.html*
```
<html>
<meta name="keywords" content="Coding, Blog">
<meta name="author" content="{{ author }}">
<head>
  <title>Blog</title>
</head>
<body>
   Welcome to my blog!

   {% for post in list_files('posts') %}
   <a href={{ post.url }}>{{ post.title }}</a>
   {% endfor %}
</body>
```

CLI
---

To build your site:

`$ smol build`

To watch for changes to your source files:

`$ smol watch`

Finally, to use a live-reloading server to see changes in real time:

`$ smol serve`

But Why?
--------

Jekyll, Hugo, et al introduce excess complexity into what should be a simple process. Smol does away with magic variables and opinionated filesystem requirements, letting you build your site however you like.


License
-------

This is free and open source software. You can use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of it,
under the terms of the [MIT License](LICENSE.md).

This software is provided "AS IS", WITHOUT WARRANTY OF ANY KIND,
express or implied. See the [MIT License](LICENSE.md) for details.