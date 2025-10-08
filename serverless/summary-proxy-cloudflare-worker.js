
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('Only POST', {status:405});
    let body;
    try { body = await request.json(); } catch { return new Response('Bad JSON', {status:400}); }
    const { pmid, prompt } = body || {};
    if (!pmid || !prompt) return new Response('Bad request', {status:400});

    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0.2,
        max_tokens: 500,
        messages: [
          {role:"system", content:"You write concise, structured summaries for clinical trials and SRs."},
          {role:"user", content: prompt}
        ]
      })
    });
    if (!resp.ok) return new Response(`OpenAI error ${resp.status}`, {status:502});
    const j = await resp.json();
    const content = j?.choices?.[0]?.message?.content?.trim() || "No content";
    const html = `<div class="ai-summary">${content}</div>`;
    return new Response(JSON.stringify({pmid, html}), {headers: {"Content-Type":"application/json"}});
  }
};
