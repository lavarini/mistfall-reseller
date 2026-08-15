# Rastreador de issues: GitHub

As issues e os PRDs deste repositório ficam no GitHub, em
`lavarini/mistfall-reseller`. Use o CLI `gh` para todas as operações.

## Convenções

- Criar: `gh issue create --title "..." --body "..."`.
- Ler: `gh issue view <numero> --comments`, incluindo rótulos e comentários.
- Listar: `gh issue list` com os filtros de estado e rótulo adequados.
- Comentar: `gh issue comment <numero> --body "..."`.
- Alterar rótulos: `gh issue edit <numero> --add-label "..."` ou
  `--remove-label "..."`.
- Fechar: `gh issue close <numero> --comment "..."`.

O repositório é inferido de `git remote -v` quando o comando roda dentro deste clone.

Quando uma skill pedir para publicar no rastreador, crie uma issue no GitHub. Quando
pedir para buscar o ticket relevante, use `gh issue view <numero> --comments`.
