# Carbon Rhythm - notas da referência visual

## Escopo da geração

- Referência: `source.png`.
- Canvas final: 1440 x 1024 px, RGB, horizontal.
- Tela: Lab Home do EvidRun Operator Console durante uma Run stub local.
- Data de geração e inspeção: 23 de julho de 2026.
- Foi feita exatamente uma chamada ao ImageGen.
- O arquivo original saiu em 1487 x 1058 px e foi apenas redimensionado de forma mecânica para 1440 x 1024 px. Não houve segunda geração.
- Nenhuma imagem da direção Evidence Ledger foi aberta, anexada ou usada.

## Direção visual

`Carbon Rhythm` combina a calma material de um console executivo de áudio com a legibilidade de um monitor de execução de precisão. A tela usa um campo dark contínuo de carbono e grafite, texto off-white quente, estrutura em cinza-prata e um único acento laranja oxidado. A profundidade vem de mudanças tonais, não de sombras ou glow.

A composição usa uma command rail horizontal compacta, um canvas operacional amplo e um Chat dock lateral subordinado. O workflow é a assinatura visual: uma trilha calibrada com cinco estágios, geometria preenchida para concluídos, laranja para o estágio atual e contorno discreto para o futuro.

Tipografia e componentes devem parecer instrumentais e precisos, mas não cyberpunk. Use uma neo-grotesca refinada para a interface e mono apenas para IDs. O sistema de forma é macio e controlado, com raio próximo de 11 px. Ícones devem vir de uma única família outline, preferencialmente Phosphor, com peso consistente entre 1.5 e 2 px.

## Elementos a preservar

- A hierarquia de dois segundos: Study, workflow, evento selecionado e composer.
- A command rail sem sidebar larga, com Lab ativo e o Project `Release Integrity` integrado.
- O disclosure `Demonstração local` claramente visível sob o título da Study.
- O workflow horizontal `Contexto`, `Subject`, `Leitura da tool`, `Avaliação`, `Evidência` como elemento dominante.
- O uso de check e contraste, sem verde, para estágios concluídos.
- `Avaliação` em laranja oxidado e `Evidência` como futuro em contorno.
- O detalhe `tool.completed: read_text`, a autorização do input local e a separação de Job, Tentativa e Run.
- As ações compactas `Abrir evidência` e `Alternar estado`.
- A separação clara entre mensagem do Usuário, preview do Agente e `Atividade observável`.
- Ícones diferentes para Tool Call e Tool Result.
- O spinner autoral de três marcas de timing imediatamente acima do composer.
- O composer largo, focado por borda laranja, com contexto de Project integrado.
- O Chat dock lateral com grip no limite interno, útil mas secundário.
- A ausência de KPIs, gráficos, tabelas de eventos, avatares de robô, glow, purple e nested cards.

## Falhas e limitações visíveis

- O Chat dock ficou mais largo do que os cerca de 250 px pedidos e ocupa aproximadamente um quarto do canvas. Na implementação, reduza-o para preservar mais área operacional.
- O dock tem uma grande área vazia. Essa calma é útil, mas a versão implementada pode usar uma altura ou largura compacta sem transformar o Chat em uma segunda página.
- O ghost tracejado de snap encosta e fica parcialmente cortado no limite direito. Trate-o apenas como pista conceitual e mantenha previews futuros dentro do viewport.
- A instrução do dock diz `Segure e arraste`, enquanto o comportamento planejado é long press no grip. A implementação deve respeitar long press e oferecer alternativa acessível por clique e teclado.
- `Alternar estado` parece quase desabilitado por causa do baixo contraste. Defina explicitamente se é ação disponível, ação futura ou controle desabilitado, com contraste coerente ao estado real.
- O status no topo e o helper do composer estão menores e mais suaves do que o ideal. Na implementação, mantenha o body real em 15-16 px equivalentes e contraste WCAG apropriado.
- O composer está um pouco mais alto do que o necessário. Preserve a largura e o foco, mas compacte a altura para não parecer um bloco decorativo.
- A trilha usa quadrados com leve aparência de botão. No código, trate os estágios como leitura de progresso sem affordance falsa, salvo quando houver navegação real.
- O cenário e as variantes não aparecem no frame. Se forem necessários ao fluxo implementado, incorpore-os como contexto secundário sem adicionar um painel novo e sem inventar métricas.
- Como toda geração raster, pequenos detalhes de ícone, kerning e alinhamento não devem ser copiados literalmente. Use componentes, fontes e ícones reais.
- A imagem mostra apenas um estado estático. Ela não valida comportamento de compactar, expandir, fechar, long press, focus, loading, erro ou reduced motion.

## Recomendações para implementação

- Use esta imagem como referência de hierarquia, anatomia, densidade e materialidade, não como especificação pixel a pixel.
- Estruture o viewport com três linhas principais: rail, conteúdo e composer; no conteúdo, use grid com canvas flexível e dock compacto.
- Comece com tokens aproximados e ajuste por contraste: carbono `#101416`, grafite `#1A1D1E`, off-white `#ECE7DE`, prata secundária `#A8A49C` e laranja oxidado `#D9652C`.
- Mantenha um único tema dark e um único acento. Não introduza verde, azul, purple ou cores extras para status.
- Use radius de 10-12 px para superfícies e 8-10 px para controles; pills somente quando a semântica exigir.
- Use Phosphor outline de forma consistente. Não redesenhe manualmente terminal, documento-check, folder, fingerprint, expand, close ou send.
- Implemente o spinner com três marcas de timing e animação de transform e opacity. Respeite `prefers-reduced-motion` com uma versão estática reconhecível.
- Garanta que completed, current e future continuem distinguíveis por shape, label e contraste, não apenas por cor.
- Preserve a natureza stub em toda copy e comportamento. Esta referência não prova uma Run real, uma evidência factual ou uma capability implementada.
- Mantenha `Atividade observável` estritamente em eventos observáveis. Não exponha chain-of-thought, raciocínio privado ou conteúdo de grader.
- Faça o grip do Chat revelar previews somente dentro dos limites do layout. Inclua operação equivalente por teclado e botão visível.
- Valide em 1440 x 1024 primeiro e depois defina o colapso responsivo. Em larguras menores, o dock deve compactar antes de comprimir o workflow.

