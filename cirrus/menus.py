from cirrus import actions

# TODO: Add a top-level Filter or Advanced action to each sub menu


def transfer_listing_menu(menu, parent, indexes):
    menu.addAction(actions.transfers.DropRowsAction(parent, indexes))


def file_listing_menu(menu, parent, files, folders, panels):
    destinations = sorted(
        {i for i in panels if i.root != parent.root},
        key=lambda x: x.root
    )
    menu.addAction(actions.search.SearchByPanelAction(parent, folders))
    menu.addAction(
        actions.listings.CreateDirectoryAction(parent, folders=folders)
    )
    if files or folders:
        menu.addAction(
            actions.listings.RemoveItemsAction(parent, files, folders)

        )
    if (files or folders) and destinations:
        menu.addSection('Transfers')
        menu.addAction(
            actions.transfers.TransferFilterAction(
                parent, folders=folders, destinations=destinations
            )
        )
        # Copy
        sub_menu = menu.addMenu('Copy')
        if files and folders:
            for destination in destinations:
                sub_menu.addAction(
                    actions.listings.CopyRecursiveItemsAction(
                        parent, files, folders, destination
                    )
                )
        else:
            if files:
                for destination in destinations:
                    sub_menu.addAction(
                        actions.listings.CopyFilesAction(
                            parent, files, destination
                        )
                    )
            elif folders:
                if len(folders) == 1:
                    for destination in destinations:
                        sub_menu.addAction(
                            actions.listings.CopyFolderAction(
                                parent, folders[0], destination
                            )
                        )
                else:
                    for destination in destinations:
                        sub_menu.addAction(
                            actions.listings.CopyFoldersAction(
                                parent, folders, destination
                            )
                        )
        # Queue
        sub_menu = menu.addMenu('Queue')
        if files and folders:
            for destination in destinations:
                sub_menu.addAction(
                    actions.listings.QueueRecursiveItemsAction(
                        parent, files, folders, destination
                    )
                )
        else:
            if files:
                for destination in destinations:
                    sub_menu.addAction(
                        actions.listings.QueueFilesAction(
                            parent, files, destination
                        )
                    )
            elif folders:
                if len(folders) == 1:
                    for destination in destinations:
                        sub_menu.addAction(
                            actions.listings.QueueFolderAction(
                                parent, folders[0], destination
                            )
                        )
                else:
                    for destination in destinations:
                        sub_menu.addAction(
                            actions.listings.QueueFoldersAction(
                                parent, folders, destination
                            )
                        )
        return sub_menu
    return menu
