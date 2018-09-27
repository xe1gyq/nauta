#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

from unittest.mock import MagicMock, call

import pytest
import yaml

from util.dependencies_checker import _is_version_valid, LooseVersion, _parse_installed_version, check_dependency, \
    DependencySpec, check_all_binary_dependencies, DEPENDENCY_MAP, NAMESPACE_PLACEHOLDER, check_os, SUPPORTED_OS_MAP, \
    get_dependency_versions_file_path, save_dependency_versions, load_dependency_versions, \
    DEPENDENCY_VERSIONS_FILE_SUFFIX
from util.exceptions import InvalidDependencyError, InvalidOsError
from cli_text_consts import UTIL_DEPENDENCIES_CHECKER_TEXTS as TEXTS


TEST_VERSION_OUTPUT = 'Client: &version.Version{SemVer:"v2.9.1",' \
                  ' GitCommit:"20adb27c7c5868466912eebdf6664e7390ebe710", GitTreeState:"clean"}'
TEST_SHORT_VERSION_OUTPUT = 'Client Version: v2.9.0\nServer Version: v2.9.1\n'
TEST_VERSION = LooseVersion('v2.9.1')


@pytest.mark.parametrize('installed_version,expected_version', [(LooseVersion('v0.0.2'), LooseVersion('v0.0.1')),
                                                                (LooseVersion('v0.0.1'), LooseVersion('v0.0.1')),
                                                                (LooseVersion('12.0.2-ce'), LooseVersion('12.0.0-ce'))])
def test_is_version_valid(installed_version, expected_version):
    assert _is_version_valid(installed_version=installed_version, expected_version=expected_version,
                             match_exact_version=False)


@pytest.mark.parametrize('installed_version,expected_version', [(LooseVersion('v0.0.2'), LooseVersion('v0.0.3')),
                                                                (LooseVersion('v0.0.1'), LooseVersion('v1.0.0')),
                                                                (LooseVersion('12.0.0-ce'), LooseVersion('12.0.2-ce'))])
def test_is_version_valid_wrong_versions(installed_version, expected_version):
    assert not _is_version_valid(installed_version=installed_version, expected_version=expected_version,
                                 match_exact_version=False)


@pytest.mark.parametrize('installed_version,expected_version', [(LooseVersion('v0.0.1'), LooseVersion('v0.0.1')),
                                                                (LooseVersion('v0.0.1'), LooseVersion('v0.0.1')),
                                                                (LooseVersion('12.0.0-ce'), LooseVersion('12.0.0-ce'))])
def test_is_version_valid_strict(installed_version, expected_version):
    assert _is_version_valid(installed_version=installed_version, expected_version=expected_version,
                             match_exact_version=True)


@pytest.mark.parametrize('installed_version,expected_version', [(LooseVersion('v0.0.2'), LooseVersion('v0.0.1')),
                                                                (LooseVersion('v0.0.1'), LooseVersion('v0.0.2')),
                                                                (LooseVersion('12.0.1-ce'), LooseVersion('12.0.0-ce'))])
def test_is_version_valid_strict_wrong_versions(installed_version, expected_version):
    assert not _is_version_valid(installed_version=installed_version, expected_version=expected_version,
                                 match_exact_version=True)


def test_parse_installed_version():
    assert _parse_installed_version(version_output=TEST_VERSION_OUTPUT, version_field='SemVer') == TEST_VERSION


def test_parse_installed_version_without_quotes():
    assert _parse_installed_version(version_output=TEST_SHORT_VERSION_OUTPUT,
                                    version_field='Server Version') == TEST_VERSION


def test_parse_installed_version_failure():
    with pytest.raises(ValueError):
        _parse_installed_version(version_output='version: 0.0.1', version_field='SemVer')


def test_check_dependency():
    test_dependency_name = 'test-dep'
    test_version = '0.0.1'
    version_command_mock = MagicMock()
    version_command_mock.return_value = test_version, 0
    test_dependency = DependencySpec(expected_version=test_version, version_command=version_command_mock,
                                     version_command_args=[], version_field=None, match_exact_version=False)

    assert check_dependency(test_dependency_name, test_dependency) == (True, LooseVersion(test_version))


def test_check_dependency_namespace():
    test_dependency_name = 'test-dep'
    test_namespace = 'test-namespace'
    test_version = '0.0.1'
    version_command_mock = MagicMock()
    version_command_mock.return_value = test_version, 0
    test_dependency = DependencySpec(expected_version=test_version, version_command=version_command_mock,
                                     version_command_args=[NAMESPACE_PLACEHOLDER], version_field=None,
                                     match_exact_version=False)

    valid_dep, installed_version = check_dependency(test_dependency_name, test_dependency, namespace=test_namespace)
    assert (valid_dep, installed_version) == (True, LooseVersion(test_version))
    version_command_mock.assert_called_with([test_namespace])


def test_check_dependency_parse():
    test_dependency_name = 'test-dep'
    test_version = LooseVersion('0.0.1')
    test_version_output = 'version:"0.0.1"'
    version_command_mock = MagicMock()
    version_command_mock.return_value = test_version_output, 0
    test_dependency = DependencySpec(expected_version=test_version, version_command=version_command_mock,
                                     version_command_args=[], version_field='version', match_exact_version=False)

    assert check_dependency(test_dependency_name, test_dependency) == (True, test_version)


def test_check_all_binary_dependencies(mocker):
    check_dependency_mock = mocker.patch('util.dependencies_checker.check_dependency')
    check_dependency_mock.return_value = True, LooseVersion('0.0.0')

    load_dependency_versions_mock = mocker.patch('util.dependencies_checker.load_dependency_versions',
                                                 return_value=None)
    save_dependency_versions_mock = mocker.patch('util.dependencies_checker.save_dependency_versions',
                                                 return_value=None)

    check_all_binary_dependencies(namespace='fake')

    assert load_dependency_versions_mock.call_count == 1, 'Saved dependency versions were not loaded.'
    assert save_dependency_versions_mock.call_count == 1, 'Dependency versions were not saved.'
    assert check_dependency_mock.call_count == len(DEPENDENCY_MAP), 'Not all dependencies were checked.'


def test_check_all_binary_dependencies_saved_versions(mocker):
    fake_namespace = 'fake'
    fake_version = LooseVersion('0.0.0')
    check_dependency_mock = mocker.patch('util.dependencies_checker.check_dependency')
    check_dependency_mock.return_value = True, fake_version

    saved_versions = {dependency_name: fake_version
                      for dependency_name in DEPENDENCY_MAP.keys()}

    load_dependency_versions_mock = mocker.patch('util.dependencies_checker.load_dependency_versions',
                                                 return_value=saved_versions)
    save_dependency_versions_mock = mocker.patch('util.dependencies_checker.save_dependency_versions',
                                                 return_value=None)

    check_all_binary_dependencies(namespace=fake_namespace)

    assert load_dependency_versions_mock.call_count == 1, 'Saved dependency versions were not loaded.'
    assert save_dependency_versions_mock.call_count == 0, 'Saved dependencies versions were overwritten.'
    assert check_dependency_mock.call_count == len(DEPENDENCY_MAP), 'Not all dependencies were checked.'
    expected_check_dependency_calls = [call(dependency_name=dependency_name, dependency_spec=dependency_spec,
                                            namespace=fake_namespace, saved_versions=saved_versions)
                                       for dependency_name, dependency_spec in DEPENDENCY_MAP.items()]
    check_dependency_mock.assert_has_calls(expected_check_dependency_calls, any_order=True)


def test_check_all_binary_dependencies_invalid_version(mocker):
    check_dependency_mock = mocker.patch('util.dependencies_checker.check_dependency')
    check_dependency_mock.return_value = False, LooseVersion('0.0.0')
    mocker.patch('util.dependencies_checker.load_dependency_versions', return_value=None)
    mocker.patch('util.dependencies_checker.save_dependency_versions', return_value=None)

    with pytest.raises(InvalidDependencyError):
        check_all_binary_dependencies(namespace='fake')


def test_check_all_binary_dependencies_parsing_error(mocker):
    check_dependency_mock = mocker.patch('util.dependencies_checker.check_dependency')
    check_dependency_mock.side_effect = ValueError
    mocker.patch('util.dependencies_checker.load_dependency_versions', return_value=None)
    mocker.patch('util.dependencies_checker.save_dependency_versions', return_value=None)

    with pytest.raises(InvalidDependencyError):
        check_all_binary_dependencies(namespace='fake')


def test_check_all_binary_dependencies_version_check_error(mocker):
    check_dependency_mock = mocker.patch('util.dependencies_checker.check_dependency')
    check_dependency_mock.side_effect = RuntimeError
    mocker.patch('util.dependencies_checker.load_dependency_versions', return_value=None)
    mocker.patch('util.dependencies_checker.save_dependency_versions', return_value=None)

    with pytest.raises(InvalidDependencyError):
        check_all_binary_dependencies(namespace='fake')


def test_check_os_unknown(mocker):
    get_os_version_mock = mocker.patch('util.dependencies_checker.get_os_version')
    get_os_version_mock.return_value = ("", LooseVersion("0"))

    with pytest.raises(InvalidOsError) as os_error:
        check_os()

    assert TEXTS["unknown_os_error_msg"] == str(os_error.value)


def test_check_os_get_os_version_fail(mocker):
    get_os_version_mock = mocker.patch('util.dependencies_checker.get_os_version')
    get_os_version_mock.side_effect = FileNotFoundError()

    with pytest.raises(InvalidOsError) as os_error:
        check_os()

    assert TEXTS["get_os_version_error_msg"] == str(os_error.value)


def test_check_os_not_supported(mocker):
    get_os_version_mock = mocker.patch('util.dependencies_checker.get_os_version')
    get_os_version_mock.return_value = ("not_supported_system", LooseVersion("9.3"))

    with pytest.raises(InvalidOsError) as os_error:
        check_os()

    assert TEXTS["unsupported_os_error_msg"].format(os_name="not_supported_system", os_version="9.3") \
        == str(os_error.value)


def test_check_os_version_not_supported(mocker):
    get_os_version_mock = mocker.patch('util.dependencies_checker.get_os_version')
    get_os_version_mock.return_value = ("ubuntu", LooseVersion("14.04"))

    with pytest.raises(InvalidOsError) as os_error:
        check_os()

    assert TEXTS["invalid_os_version_error_msg"].format(os_name="ubuntu", os_version="14.04") == str(os_error.value)


def test_check_os_version_supported(mocker):
    get_os_version_mock = mocker.patch('util.dependencies_checker.get_os_version')
    get_os_version_mock.return_value = (list(SUPPORTED_OS_MAP.keys())[0],
                                        SUPPORTED_OS_MAP[list(SUPPORTED_OS_MAP.keys())[0]])

    try:
        check_os()
    except InvalidOsError:
        pytest.fail("check_os failed with supported OS.")


def test_get_dependency_version_file_path(mocker):
    fake_dlsctl_version = '1.0.0-alpha'
    fake_config_path = '/usr/ogorek/dlsctl_config'
    mocker.patch('util.dependencies_checker.VERSION', fake_dlsctl_version)
    fake_config = mocker.patch('util.dependencies_checker.Config')
    fake_config.return_value.config_path = fake_config_path

    path = get_dependency_versions_file_path()
    assert path in {f'{fake_config_path}/{fake_dlsctl_version}{DEPENDENCY_VERSIONS_FILE_SUFFIX}',
                    f'{fake_config_path}\\{fake_dlsctl_version}{DEPENDENCY_VERSIONS_FILE_SUFFIX}'}  # Windows


def test_save_dependency_versions(mocker, tmpdir):
    fake_config_dir = tmpdir.mkdir("/dlsctl_config")
    fake_dependency_versions_file_path = f'{fake_config_dir}1.0.0.saved-versions.yaml'
    mocker.patch('util.dependencies_checker.get_dependency_versions_file_path',
                 return_value=fake_dependency_versions_file_path)
    fake_dependency_versions = {'bla': LooseVersion('1.0.0'),
                                'ble': LooseVersion('0.0.1-alpha')}
    save_dependency_versions(fake_dependency_versions)

    with open(fake_dependency_versions_file_path, mode='r', encoding='utf-8') as dep_versions_file:
        assert yaml.load(dep_versions_file) == fake_dependency_versions


def test_load_dependency_versions(mocker, tmpdir):
    fake_dependency_versions = {'bla': LooseVersion('1.0.0'),
                                'ble': LooseVersion('0.0.1-alpha')}
    fake_dependency_versions_file = tmpdir.mkdir("/dlsctl_config").join("1.0.0.saved-versions.yaml")
    fake_dependency_versions_file.write(yaml.dump(fake_dependency_versions))

    mocker.patch('util.dependencies_checker.get_dependency_versions_file_path',
                 return_value=fake_dependency_versions_file)

    assert fake_dependency_versions == load_dependency_versions()
