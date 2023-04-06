from typing import Optional, Union

import pytest

from acc_py_index.simple import model, parser


def test_parse_json_project_page() -> None:
    page = '''
    {
        "meta": {
            "api-version": "1.0"
        },
        "name": "holygrail",
        "files": [
            {
                "filename": "holygrail-1.0.tar.gz",
                "url": "https://example.com/files/holygrail-1.0.tar.gz",
                "hashes": {"sha256": "...", "blake2b": "..."},
                "requires-python": ">=3.7",
                "yanked": "Had a vulnerability"
            },
            {
                "filename": "holygrail-1.0-py3-none-any.whl",
                "url": "holygrail-1.0-py3-none-any.whl",
                "hashes": {},
                "dist-info-metadata": true
            },
            {
                "filename": "holygrail-1.1-py3-none-any.whl",
                "url": "holygrail-1.0-py3-none-any.whl",
                "hashes": {},
                "dist-info-metadata": {"sha256": "..."},
                "yanked": true
            }
        ]

    }'''

    result = parser.parse_json_project_page(page)

    assert result == model.ProjectDetail(
        model.Meta("1.0"),
        "holygrail",
        [
            model.File(
                filename="holygrail-1.0.tar.gz",
                url="https://example.com/files/holygrail-1.0.tar.gz",
                hashes={"sha256": "...", "blake2b": "..."},
                requires_python=">=3.7",
                yanked="Had a vulnerability",
            ),
            model.File(
                filename="holygrail-1.0-py3-none-any.whl",
                url="holygrail-1.0-py3-none-any.whl",
                hashes={},
                dist_info_metadata=True,
            ),
            model.File(
                filename="holygrail-1.1-py3-none-any.whl",
                url="holygrail-1.0-py3-none-any.whl",
                hashes={},
                dist_info_metadata={"sha256": "..."},
                yanked=True,
            ),
        ],
    )


def test_parse_html_project_page() -> None:
    page = '''
        <a href="holygrail-1.0.tar.gz#sha256=..."
            data-requires-python="&gt;=3.7"
        >holygrail-1.0.tar.gz</a>

        <a href="holygrail-1.1-py3-none-any.whl"
        >holygrail-1.1-py3-none-any.whl</a>

        <a>bad-project.whl</a>
        <a href="bad-project.whl></a>
    '''

    result = parser.parse_html_project_page(page, "holygrail")

    assert result == model.ProjectDetail(
        model.Meta("1.0"),
        "holygrail",
        [
            model.File(
                filename="holygrail-1.0.tar.gz",
                url="holygrail-1.0.tar.gz",
                hashes={"sha256": "..."},
                requires_python=">=3.7",
            ),
            model.File(
                filename="holygrail-1.1-py3-none-any.whl",
                url="holygrail-1.1-py3-none-any.whl",
                hashes={},
            ),
        ],
    )


@pytest.mark.parametrize(
    "yank_attr, yank_value",
    [
        ('data-yanked', True),
        ('data-yanked=""', True),
        ('data-yanked="reason"', "reason"),
        ('', None),
    ],
)
def test_parse_html_project_page_yank(
    yank_attr: str,
    yank_value: Optional[Union[bool, str]],
) -> None:
    page = f'''
        <a href="holygrail-1.0.tar.gz"
            {yank_attr}
        >holygrail-1.0.tar.gz</a>
    '''

    result = parser.parse_html_project_page(page, "holygrail")

    assert result == model.ProjectDetail(
        model.Meta("1.0"),
        "holygrail",
        [
            model.File(
                filename="holygrail-1.0.tar.gz",
                url="holygrail-1.0.tar.gz",
                hashes={},
                yanked=yank_value,
            ),
        ],
    )


@pytest.mark.parametrize(
    "metadata_attr, metadata_value",
    [
        ('data-dist-info-metadata', True),
        ('data-dist-info-metadata="true"', True),
        ('data-dist-info-metadata="sha=..."', {"sha": "..."}),
        ('', None),
    ],
)
def test_parse_html_project_page_metadata(
    metadata_attr: str,
    metadata_value: Optional[Union[bool, dict[str, str]]],
) -> None:
    page = f'''
        <a href="holygrail-1.0.tar.gz"
            {metadata_attr}
        >holygrail-1.0.tar.gz</a>
    '''

    result = parser.parse_html_project_page(page, "holygrail")

    assert result == model.ProjectDetail(
        model.Meta("1.0"),
        "holygrail",
        [
            model.File(
                filename="holygrail-1.0.tar.gz",
                url="holygrail-1.0.tar.gz",
                hashes={},
                dist_info_metadata=metadata_value,
            ),
        ],
    )


@pytest.mark.parametrize(
    "gpg_attr, gpg_value",
    [
        ('data-gpg-sig="true"', True),
        ('data-gpg-sig="false"', False),
        ('', None),
        ('data-gpg-sig="invalid"', None),
    ],
)
def test_parse_html_project_page_gpg(gpg_attr: str, gpg_value: Optional[bool]) -> None:
    page = f'''
        <a href="holygrail-1.0.tar.gz"
            {gpg_attr}
        >holygrail-1.0.tar.gz</a>
    '''

    result = parser.parse_html_project_page(page, "holygrail")

    assert result == model.ProjectDetail(
        model.Meta("1.0"),
        "holygrail",
        [
            model.File(
                filename="holygrail-1.0.tar.gz",
                url="holygrail-1.0.tar.gz",
                hashes={},
                gpg_sig=gpg_value,
            ),
        ],
    )


def test_parse_json_project_list() -> None:
    page = '''
    {
        "meta": {
            "api-version": "1.0"
        },
        "projects": [
            {
                "name": "gym"
            },
            {
                "name": "acc_py_index"
            }
        ]
    }'''

    result = parser.parse_json_project_list(page)

    assert result == model.ProjectList(
        model.Meta("1.0"),
        {
            model.ProjectListElement("gym"),
            model.ProjectListElement("acc_py_index"),
        },
    )


def test_parse_html_project_list() -> None:
    page = '''
        <a href="url">gym</a>
        <a href="url">acc_py_index</a>
    '''

    result = parser.parse_html_project_list(page)

    assert result == model.ProjectList(
        model.Meta("1.0"),
        {
            model.ProjectListElement("gym"),
            model.ProjectListElement("acc_py_index"),
        },
    )
