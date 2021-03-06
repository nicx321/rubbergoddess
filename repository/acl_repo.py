from typing import Optional, List

from repository.base_repository import BaseRepository
from repository.database import session
from repository.database.acl import ACL_rule, ACL_group, ACL_rule_user, ACL_rule_group


class ACLRepository(BaseRepository):
    def __init__(self):
        super().__init__()

    ##
    ## Groups
    ##

    def get_groups(self, guild_id: int) -> Optional[List[ACL_group]]:
        return session.query(ACL_group).filter(ACL_group.guild_id == guild_id).all()

    def get_group(self, guild_id: int, name: str) -> Optional[ACL_group]:
        return (
            session.query(ACL_group)
            .filter(ACL_group.guild_id == guild_id, ACL_group.name == name)
            .one_or_none()
        )

    def get_group_by_role(self, role_id: int) -> Optional[ACL_group]:
        return session.query(ACL_group).filter(ACL_group.role_id == role_id).one_or_none()

    def add_group(self, guild_id: int, name: str, parent: str, role_id: int) -> ACL_group:
        if parent is not None and self.get_group(guild_id, parent) is None:
            raise NotFound(guild_id=guild_id, name=parent)

        if self.get_group(guild_id, name) is not None:
            raise Duplicate(guild_id=guild_id, name=name)

        if role_id > 0 and self.get_group_by_role(role_id) is not None:
            raise Duplicate(role_id=role_id)

        group = ACL_group(guild_id=guild_id, name=name, parent=parent, role_id=role_id)
        session.add(group)
        session.commit()

        return group

    def edit_group(
        self,
        guild_id: int,
        name: str,
        *,
        new_name: str = None,
        parent: str = None,
        role_id: int = None,
    ) -> ACL_group:
        group = self.get_group(guild_id, name)
        if group is None:
            raise NotFound(guild_id=guild_id, name=name)

        if new_name is not None:
            name = new_name
            group.name = name
        if parent is not None:
            if self.get_group(guild_id, parent) is None:
                raise NotFound(guild_id=guild_id, name=parent)
            group.parent = parent
        if role_id is not None:
            group.role_id = role_id

        session.commit()
        return group

    def delete_group(self, guild_id: int, name: str) -> dict:
        group = self.get_group(guild_id, name)
        if group is None:
            raise NotFound(guild_id=guild_id, name=name)

        result = group.one().mirror()
        group.delete()
        session.commit()

        return result

    ##
    ## Rules
    ##

    def get_rules(self, guild_id: int) -> Optional[List[ACL_rule]]:
        return session.query(ACL_rule).filter(ACL_rule.guild_id == guild_id).all()

    def get_rule(self, guild_id: int, command: str) -> Optional[ACL_rule]:
        return (
            session.query(ACL_rule)
            .filter(ACL_rule.guild_id == guild_id, ACL_rule.command == command)
            .one_or_none()
        )

    def add_rule(self, guild_id: int, command: str, allow: bool = False) -> ACL_rule:
        if self.get_rule(guild_id, command) is not None:
            raise Duplicate(guild_id=guild_id, command=command)

        rule = ACL_rule(guild_id=guild_id, command=command, default=allow)
        session.add(rule)
        session.commit()
        return rule

    def edit_rule(self, guild_id: int, command: str, allow: bool) -> ACL_rule:
        rule = self.get_rule(guild_id, command)
        if rule is None:
            raise NotFound(guild_id=guild_id, command=command)
        rule.default = allow
        session.commit()
        return rule

    def delete_rule(self, guild_id: int, command: str) -> dict:
        if self.get_rule(guild_id, command) is None:
            raise NotFound(guild_id=guild_id, command=command)

        rule = session.query(ACL_rule).filter(
            ACL_rule.guild_id == guild_id, ACL_rule.command == command
        )

        result = rule.one().mirror()
        rule.delete()
        session.commit()
        return result

    def delete_rules(self, guild_id: int) -> int:
        return session.query(ACL_rule).filter(ACL_rule.guild_id == guild_id).delete()

    ##
    ## Constraints
    ##

    def add_group_constraint(self, guild_id: int, command: str, name: str, allow: bool) -> ACL_rule:
        group = self.get_group(guild_id, name)
        if group is None:
            raise NotFound(guild_id=guild_id, name=name)

        rule = self.get_rule(guild_id, command)
        if rule is None:
            raise NotFound(guild_id=guild_id, command=command)

        rule.groups.append(ACL_rule_group(group_id=group.id, allow=allow))
        session.commit()
        return rule

    def remove_group_constraint(self, constraint_id: int) -> bool:
        result = session.query(ACL_rule_group).filter(ACL_rule_group.id == constraint_id).delete()
        session.commit()
        return result > 0

    def add_user_constraint(
        self, guild_id: int, command: str, user_id: int, allow: bool
    ) -> ACL_rule:
        rule = self.get_rule(guild_id, command)
        if rule is None:
            raise NotFound(guild_id=guild_id, command=command)

        rule.users.append(ACL_rule_user(user_id=user_id, allow=allow))
        session.commit()
        return rule

    def remove_user_constraint(self, constraint_id: int) -> bool:
        result = session.query(ACL_rule_user).filter(ACL_rule_user.id == constraint_id).delete()
        session.commit()
        return result > 0


class ACLException(Exception):
    def __init__(self, message: str, **parameters):
        self.message = message or "ACL exception"

        self.parameters = parameters

        super().__init__(self.__repr__())

    def __repr__(self):
        params = ", ".join([f"{param}={value}" for param, value in self.parameters.items()])
        return f"{self.message}: {params}."

    def __str__(self):
        return self.__repr__()


class NotFound(ACLException):
    def __init__(self, **parameters):
        super().__init__("Not found", **parameters)


class Duplicate(ACLException):
    def __init__(self, **parameters):
        super().__init__("Duplicate", **parameters)
