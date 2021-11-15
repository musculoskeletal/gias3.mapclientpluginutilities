"""
FILE: mayaviviewerdatapoints.py
LAST MODIFIED: 24-12-2015 
DESCRIPTION: Container class for datapoints in a mayavi scene.

===============================================================================
This file is part of GIAS2. (https://bitbucket.org/jangle/gias2)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
===============================================================================
"""

from gias3.mapclientpluginutilities.viewers.mayaviviewerobjects import MayaviViewerSceneObject, MayaviViewerObject, colours


class MayaviViewerDataPointsSceneObject(MayaviViewerSceneObject):
    typeName = 'datapoints'

    def __init__(self, name, points):
        super().__init__()
        self.name = name
        self.points = points

    def setVisibility(self, visible):
        self.points.visible = visible

    def remove(self):
        self.points.remove()
        self.points = None


class MayaviViewerDataPoints(MayaviViewerObject):
    typeName = 'datapoints'

    def __init__(self, name, coordinates, scalars=None, render_args=None):
        super().__init__()
        self.name = name
        self._coordinates = coordinates

        self.scalarName = 'None'
        if scalars is None:
            self.scalars = {}
        else:
            self.scalars = scalars

        if render_args is None:
            self.renderArgs = {}
        else:
            self.renderArgs = render_args

        self.sceneObject = None
        self.defaultColour = colours['bone']
        if 'color' not in list(self.renderArgs.keys()):
            self.renderArgs['color'] = self.defaultColour

    def setScalarSelection(self, scalarName):
        self.scalarName = scalarName

    def setVisibility(self, visible):
        self.sceneObject.setVisibility(visible)

    def remove(self):
        self.sceneObject.remove()
        self.sceneObject = None

    def draw(self, scene):
        scene.disable_render = True
        d = self._coordinates
        s = self.scalars.get(self.scalarName)
        renderArgs = self.renderArgs
        if s is not None:
            self.sceneObject = MayaviViewerDataPointsSceneObject(self.name,
                                                                 scene.mlab.points3d(d[:, 0], d[:, 1], d[:, 2], s,
                                                                                     **renderArgs))
        else:
            self.sceneObject = MayaviViewerDataPointsSceneObject(self.name,
                                                                 scene.mlab.points3d(d[:, 0], d[:, 1], d[:, 2],
                                                                                     **renderArgs))

        scene.disable_render = False
        return self.sceneObject

    def updateGeometry(self, coordinates, scene):

        if self.sceneObject is None:
            self._coordinates = coordinates
            self.draw(scene)
        else:
            self.sceneObject.points.mlab_source.set(x=coordinates[:, 0], y=coordinates[:, 1], z=coordinates[:, 2])
            self._coordinates = coordinates

    def updateScalar(self, scalar_name, scene):
        self.setScalarSelection(scalar_name)
        if self.sceneObject is None:
            self.draw(scene)
        else:
            d = self._coordinates
            s = self.scalars.get(self.scalarName)
            renderArgs = self.renderArgs
            if s is not None:
                self.sceneObject.points.actor.mapper.scalar_visibility = True
                self.sceneObject.points.mlab_source.reset(x=d[:, 0], y=d[:, 1], z=d[:, 2], s=s)
            else:
                if 'color' not in renderArgs:
                    color = self.defaultColour
                else:
                    color = renderArgs['color']

                self.sceneObject.points.actor.mapper.scalar_visibility = False
                self.sceneObject.points.actor.property.specular_color = color
                self.sceneObject.points.actor.property.diffuse_color = color
                self.sceneObject.points.actor.property.ambient_color = color
                self.sceneObject.points.actor.property.color = color
                self.sceneObject.points.mlab_source.reset(x=d[:, 0], y=d[:, 1], z=d[:, 2])
