# Where to work

Read before you read or edit product files. Where you work depends on where the product stores them.

## Find the storage option

With a saved Inwoven key, send `GET https://backlog.works/api/v1/products/<id>/files/backlog` with `Authorization: Bearer <key>`.
`<id>` is the product id from the setup answer. Act on the answer:

- 200: Inwoven stores the files. The option is Inwoven only or GitHub and Inwoven. Work through the API.
- 409 `not_hosted`: the option is GitHub only, or Inwoven does not store this file yet. Work in your checkout.
- 401: the key ended. Work in your checkout. A key from a setup approved on the link ends when the product connects a repository.
- No key: work in your checkout.

## Inwoven only

Read and write through the API. Nothing is in a repository.
GET returns the Markdown and an `ETag`. PUT the whole file with `Content-Type: text/markdown` and `If-Match: <ETag>`. `If-Match: 0` creates a missing file.
The API has backlog, goals and impact. It has no wardley.md and no learnings.md.

## GitHub and Inwoven

Read and write backlog, goals and impact through the API, also when you have a checkout. The calls are the same.
People see your change within seconds. Inwoven commits it to the repository within 5 minutes, or once a day when the person set that.
The answer to a PUT has the header `Inwoven-GitHub`: `state` is `waiting`, `retrying` or `sent`.
The API also answers while GitHub is down.
The file in your checkout can be older than Inwoven's text: take the text you edit from GET, not from the checkout.
Inwoven also merges a commit you push to these files, but people see it later. Push them only when you have no key.
Edit wardley.md and learnings.md in the checkout: the API does not have them.

## GitHub only

Inwoven stores none of the files, and the API answers 409 `not_hosted`.
Work in your checkout: pull, edit, then commit and push when the person or the repo instructions ask.

## When a write is refused

- 412 `stale`: someone saved first. Nothing was overwritten. GET again, merge your change into that text, then PUT with the new `ETag`.
- 409 `not_hosted` on a write: edit the file in your checkout.
- 422: the file breaks the format. `messages` says where. Fix it and PUT again. Nothing was changed.
