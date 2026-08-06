from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.routers.auth import require_auth

router = APIRouter()


@router.get("/")
async def methods_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    methods = [
        {
            "name": "Pomodoro",
            "icon": "\U0001f345",
            "description": "Trabalhe por 25 minutos e descanse por 5. A cada 4 ciclos, descanse por 15-30 minutos.",
            "tips": [
                "Use o cronometro do DevJourney",
                "Nao interrompa durante 25 minutos",
                "Descanse os olhos olhando para longe",
                "Anote quantos pomodoros fez no dia",
            ],
        },
        {
            "name": "Ativa Reciproca",
            "icon": "\U0001f9e0",
            "description": "Alterne entre materias diferentes para manter o cerebro ativo e evitar fadiga.",
            "tips": [
                "Estude 1 hora de uma materia, depois troque",
                "Combine materias dificeis com mais faceis",
                "Revise o que estudou no dia anterior",
                "Use mapas mentais para conectar conceitos",
            ],
        },
        {
            "name": "Espacamento",
            "icon": "\U0001f4c5",
            "description": "Revise o conteudo em intervalos crescentes: 1 dia, 3 dias, 7 dias, 15 dias, 30 dias.",
            "tips": [
                "Crie um calendario de revisao",
                "Use o sistema de habitos para marcar revisoes",
                "Anote as datas de revisao no calendario",
                "Revise antes de dormir para melhor fixacao",
            ],
        },
        {
            "name": "Pratica Ativa",
            "icon": "\u270d\ufe0f",
            "description": "Nao apenas leia, faca exercicios e resolva problemas ativamente.",
            "tips": [
                "Resolva questoes de provas anteriores",
                "Implemente projetos praticos",
                "Explique o conteudo para outra pessoa",
                "Crie flashcards e teste-se",
            ],
        },
        {
            "name": "Mapa Mental",
            "icon": "\U0001f333",
            "description": "Organize visualmente as informacoes para melhor compreensao e memorizacao.",
            "tips": [
                "Comece pelo conceito central",
                "Use cores diferentes por tema",
                "Conecte ideias com setas",
                "Revise e atualize regularmente",
            ],
        },
        {
            "name": "Feynman",
            "icon": "\U0001f4a1",
            "description": "Explique o conteudo como se ensinasse para uma crianca. Se nao conseguir, volte a estudar.",
            "tips": [
                "Escreva com suas palavras",
                "Use analogias do dia a dia",
                "Identifique onde travou",
                "Simplifique ao maximo",
            ],
        },
    ]

    return request.app.state.templates.TemplateResponse(
        request,
        "methods.html",
        context={"methods": methods},
    )
