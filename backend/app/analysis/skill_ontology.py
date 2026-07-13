from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    canonical_name: str
    category: str
    aliases: tuple[str, ...]
    related_concepts: tuple[str, ...] = ()
    notes: str = ""


SKILL_ONTOLOGY: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        canonical_name="Python",
        category="programming_language",
        aliases=("python",),
    ),
    SkillDefinition(
        canonical_name="Java",
        category="programming_language",
        aliases=("java",),
        notes="Keep separate from JavaScript.",
    ),
    SkillDefinition(
        canonical_name="C#",
        category="programming_language",
        aliases=("c#", "c sharp", "csharp"),
    ),
    SkillDefinition(
        canonical_name="JavaScript",
        category="programming_language",
        aliases=("javascript", "js"),
        notes="Keep separate from Java.",
    ),
    SkillDefinition(
        canonical_name="TypeScript",
        category="programming_language",
        aliases=("typescript", "ts"),
    ),
    SkillDefinition(
        canonical_name="HTML",
        category="frontend",
        aliases=("html", "html5"),
    ),
    SkillDefinition(
        canonical_name="CSS",
        category="frontend",
        aliases=("css", "css3"),
    ),
    SkillDefinition(
        canonical_name="Sass",
        category="frontend",
        aliases=("sass", "scss"),
    ),
    SkillDefinition(
        canonical_name="SQL",
        category="database",
        aliases=(
            "sql",
            "relational database",
            "relational databases",
            "database queries",
            "database querying",
        ),
    ),
    SkillDefinition(
        canonical_name="PostgreSQL",
        category="database",
        aliases=("postgresql", "postgres"),
        related_concepts=("SQL",),
    ),
    SkillDefinition(
        canonical_name="MySQL",
        category="database",
        aliases=("mysql",),
        related_concepts=("SQL",),
    ),
    SkillDefinition(
        canonical_name="Entity Framework Core",
        category="database",
        aliases=("entity framework core", "entity framework", "ef core"),
        related_concepts=("ORM",),
    ),
    SkillDefinition(
        canonical_name="ORM",
        category="database",
        aliases=(
            "orm",
            "object-relational mapping",
            "object relational mapping",
            "object-relational mapping frameworks",
            "object relational mapping frameworks",
        ),
    ),
    SkillDefinition(
        canonical_name="React",
        category="frontend",
        aliases=("react", "react.js", "reactjs"),
    ),
    SkillDefinition(
        canonical_name="Angular",
        category="frontend",
        aliases=("angular", "angular.js", "angularjs"),
    ),
    SkillDefinition(
        canonical_name="Responsive Web Apps",
        category="frontend",
        aliases=(
            "responsive web application",
            "responsive web applications",
            "responsive web app",
            "responsive web apps",
        ),
    ),
    SkillDefinition(
        canonical_name="Node.js",
        category="backend",
        aliases=("node.js", "nodejs", "node"),
        related_concepts=("JavaScript",),
    ),
    SkillDefinition(
        canonical_name=".NET",
        category="backend",
        aliases=(".net", "dotnet", "asp.net", "asp net"),
        related_concepts=("C#",),
    ),
    SkillDefinition(
        canonical_name="ASP.NET Core",
        category="backend",
        aliases=("asp.net core", "asp net core", "aspnet core"),
        related_concepts=(".NET", "C#"),
    ),
    SkillDefinition(
        canonical_name="FastAPI",
        category="backend",
        aliases=("fastapi",),
        related_concepts=("REST APIs", "Python"),
    ),
    SkillDefinition(
        canonical_name="REST APIs",
        category="backend",
        aliases=(
            "rest api",
            "rest apis",
            "restful api",
            "restful apis",
            "restful service",
            "restful services",
            "api development",
            "api endpoints",
            "backend endpoints",
            "web api",
            "web apis",
            "web services",
            "robust apis",
        ),
    ),
    SkillDefinition(
        canonical_name="Service-Oriented Architecture",
        category="software_architecture",
        aliases=("service-oriented architecture", "service oriented architecture", "soa"),
        related_concepts=("REST APIs",),
    ),
    SkillDefinition(
        canonical_name="Event-Driven Architecture",
        category="software_architecture",
        aliases=(
            "event-driven architecture",
            "event driven architecture",
            "event-based software design",
            "event based software design",
        ),
    ),
    SkillDefinition(
        canonical_name="Software Architecture",
        category="software_architecture",
        aliases=(
            "software architecture",
            "architecture decisions",
            "design strategies",
            "scalable and maintainable solutions",
        ),
    ),
    SkillDefinition(
        canonical_name="OOP",
        category="software_design",
        aliases=(
            "oop",
            "object-oriented programming",
            "object oriented programming",
            "object-oriented design",
            "object oriented design",
            "oop concepts",
        ),
    ),
    SkillDefinition(
        canonical_name="Design Patterns",
        category="software_design",
        aliases=("design patterns", "software design patterns"),
    ),
    SkillDefinition(
        canonical_name="Full-Stack Development",
        category="full_stack",
        aliases=(
            "full-stack development",
            "full stack development",
            "full-stack",
            "full stack",
            "front end, business logic, and data access layers",
            "front end business logic and data access layers",
        ),
    ),
    SkillDefinition(
        canonical_name="Software Development Lifecycle",
        category="software_engineering",
        aliases=(
            "development lifecycle",
            "planning to release and support",
            "release and support",
            "developing software",
            "software development",
        ),
    ),
    SkillDefinition(
        canonical_name="Code Review",
        category="software_engineering",
        aliases=("code review", "code reviews"),
    ),
    SkillDefinition(
        canonical_name="Docker",
        category="devops",
        aliases=(
            "docker",
            "containerization",
            "containers",
            "containerized",
            "containerized applications",
            "containerized workloads",
        ),
    ),
    SkillDefinition(
        canonical_name="Kubernetes",
        category="devops",
        aliases=("kubernetes", "k8s", "container orchestration"),
    ),
    SkillDefinition(
        canonical_name="AWS",
        category="cloud",
        aliases=("aws", "amazon web services"),
    ),
    SkillDefinition(
        canonical_name="Azure",
        category="cloud",
        aliases=("azure", "microsoft azure"),
    ),
    SkillDefinition(
        canonical_name="Linux",
        category="systems",
        aliases=("linux", "unix"),
    ),
    SkillDefinition(
        canonical_name="Windows Server",
        category="systems",
        aliases=("windows server",),
    ),
    SkillDefinition(
        canonical_name="Git",
        category="developer_tools",
        aliases=("git", "github", "version control", "source control"),
        notes="GitHub Actions should not prove Git by itself.",
    ),
    SkillDefinition(
        canonical_name="CI/CD",
        category="devops",
        aliases=(
            "ci/cd",
            "continuous integration",
            "continuous deployment",
            "continuous delivery",
            "github actions",
            "build pipeline",
            "build pipelines",
            "deployment pipeline",
            "deployment pipelines",
        ),
    ),
    SkillDefinition(
        canonical_name="Agile",
        category="process",
        aliases=("agile", "scrum", "agile team-based environment", "agile team based environment"),
    ),
    SkillDefinition(
        canonical_name="Testing",
        category="quality",
        aliases=(
            "testing",
            "unit testing",
            "automated test",
            "automated tests",
            "automated testing",
            "test automation",
            "test suite",
            "test coverage",
        ),
    ),
    SkillDefinition(
        canonical_name="Machine Learning",
        category="ai_ml",
        aliases=("machine learning", "ml", "artificial intelligence", "ai"),
    ),
    SkillDefinition(
        canonical_name="Data Pipelines",
        category="data",
        aliases=("data pipeline", "data pipelines", "etl"),
    ),
    SkillDefinition(
        canonical_name="Scripting",
        category="automation",
        aliases=("scripting", "automation scripting", "script", "automation scripts"),
    ),
)


SKILL_PATTERNS: dict[str, list[str]] = {
    skill.canonical_name: list(skill.aliases)
    for skill in SKILL_ONTOLOGY
}

SKILL_CATEGORIES: dict[str, str] = {
    skill.canonical_name: skill.category
    for skill in SKILL_ONTOLOGY
}

RELATED_SKILLS: dict[str, list[str]] = {
    skill.canonical_name: list(skill.related_concepts)
    for skill in SKILL_ONTOLOGY
    if skill.related_concepts
}
