/* Custom MD - tiny dependency-free syntax highlighter for preview code blocks.
 *
 * Runs on the already-sanitized preview DOM: the caller reads `code.textContent`
 * and replaces it with this tokenizer's output. The output contains ONLY
 * HTML-escaped source text plus <span class="tok-..."> wrappers — it never
 * reflects raw input, so re-inserting it cannot introduce markup or scripts.
 *
 * Supported languages (aliases on the right):
 *   js, ts, python, html, css, json, bash, sql
 * Unknown / missing language -> escaped plain text (no spans).
 */
(function (global) {
  "use strict";

  var ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  function esc(s) { return s.replace(/[&<>"']/g, function (c) { return ESC[c]; }); }

  function kw(words) {
    return new RegExp("\\b(?:" + words.split(/\s+/).join("|") + ")\\b");
  }

  var RULES = {
    js: [
      ["comment", /\/\/[^\n]*|\/\*[\s\S]*?\*\//],
      ["string", /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`/],
      ["keyword", kw("const let var function return if else for while of in new class extends import export from async await try catch finally throw switch case break continue typeof instanceof this null undefined true false static get set delete yield default do")],
      ["builtin", kw("console document window Math JSON Object Array String Number Boolean Promise Set Map require module globalThis fetch process")],
      ["number", /\b\d+(?:\.\d+)?\b/],
      ["func", /[A-Za-z_$][\w$]*(?=\s*\()/],
      ["punct", /[{}()[\];,.:]/]
    ],
    python: [
      ["comment", /#[^\n]*/],
      ["string", /"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/],
      ["decorator", /@\w+/],
      ["keyword", kw("def class return if elif else for while in not and or import from as try except finally raise with lambda pass yield global nonlocal assert break continue del is None True False async await")],
      ["builtin", kw("print len range type str int float list dict set tuple open enumerate zip map filter sum min max sorted reversed isinstance super self")],
      ["number", /\b\d+(?:\.\d+)?\b/],
      ["func", /[A-Za-z_]\w*(?=\s*\()/],
      ["punct", /[{}()[\];,.:]/]
    ],
    html: [
      ["comment", /<!--[\s\S]*?-->/],
      ["tag", /<\/?[a-zA-Z][\w-]*/],
      ["attr", /\b[a-zA-Z-]+(?==)/],
      ["string", /"[^"]*"|'[^']*'/],
      ["punct", /[<>/=]|</],
      ["comment", /<\/[a-zA-Z][\w-]*>/]
    ],
    css: [
      ["comment", /\/\*[\s\S]*?\*\//],
      ["prop", /[a-zA-Z-]+(?=\s*:)/],
      ["number", /\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|vmin|vmax|s|ms|deg|fr)?\b/],
      ["hex", /#[0-9a-fA-F]{3,8}\b/],
      ["string", /"[^"]*"|'[^']*'/],
      ["pseudo", /::?[a-zA-Z-]+/],
      ["punct", /[{}();,]/]
    ],
    json: [
      ["key", /"(?:[^"\\]|\\.)*"(?=\s*:)/],
      ["string", /"(?:[^"\\]|\\.)*"/],
      ["literal", /\b(?:true|false|null)\b/],
      ["number", /-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/],
      ["punct", /[{}[\],:]/]
    ],
    bash: [
      ["comment", /#[^\n]*/],
      ["string", /"(?:\\.|[^"\\])*"|'[^']*'/],
      ["builtin", kw("echo cd ls mkdir rm cp mv cat grep sed awk find chmod sudo git npm pip python python3 export source alias touch pwd head tail wc sort uniq tar curl wget kill ps top sh bash")],
      ["flag", /--?[a-zA-Z][a-zA-Z-]*/],
      ["var", /\$[A-Za-z_][\w]*|\$\{[\w]+\}/],
      ["number", /\b\d+\b/],
      ["punct", /[|;&<>()]/]
    ],
    sql: [
      ["comment", /--[^\n]*|\/\*[\s\S]*?\*\//],
      ["string", /'[^']*'|"(?:[^"\\]|\\.)*"/],
      ["keyword", kw("select from where insert into values update set delete create table drop alter join left right inner outer on as and or not null group by order having limit offset distinct count sum avg min max in exists between like primary key foreign references union all case when then else end index")],
      ["number", /\b\d+(?:\.\d+)?\b/],
      ["punct", /[(),.;]/]
    ]
  };

  var ALIASES = {
    js: "js", javascript: "js", jsx: "js", ts: "js", typescript: "js", tsx: "js",
    python: "python", py: "python",
    html: "html", xml: "html",
    css: "css",
    json: "json",
    bash: "bash", sh: "bash", shell: "bash", console: "bash",
    sql: "sql"
  };

  function norm(lang) {
    if (!lang) return null;
    var key = String(lang).toLowerCase();
    return ALIASES[key] || null;
  }

  // Left-to-right scan: at each position the longest matching rule wins; text
  // between matches is escaped verbatim. Zero-length matches are impossible
  // with the rules above (every pattern consumes at least one char).
  function highlight(code, lang) {
    var rules = RULES[norm(lang)];
    var out = "";
    var i = 0;
    var len = code.length;

    if (!rules) return esc(code);

    while (i < len) {
      var best = null;
      for (var r = 0; r < rules.length; r++) {
        var rule = rules[r];
        rule[1].lastIndex = i;
        var m = rule[1].exec(code);
        if (m && m.index === i && (!best || m[0].length > best.m[0].length)) {
          best = { type: rule[0], m: m };
        }
      }
      if (!best) {
        out += esc(code.charAt(i));
        i++;
      } else {
        out += '<span class="tok-' + best.type + '">' + esc(best.m[0]) + "</span>";
        i += best.m[0].length;
      }
    }
    return out;
  }

  global.highlightCode = highlight;
})(window);